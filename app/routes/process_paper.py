import base64
import uuid
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from flask import request, Blueprint, Response as FlaskResponse, stream_with_context, current_app

from app import db
from app.models.paper import Paper, SessionPaperMapping, Folder
from app.utils.file_utils import calculate_file_hash
from app.utils.pdf_handler import PDFHandler
from app.constant.standard_response import Response
from app.utils.chat_manager import ChatContextManager
from app.api_functions.contextual_QA import process_paper, get_chat_chain
from app.utils.get_prompts import get_summary_prompt
from app.api_functions.literature_review import generate_literature_review_stream

ocr_bp = Blueprint('ocr', __name__)
pdf_handler = PDFHandler()
logger = logging.getLogger(__name__)

@ocr_bp.route('/process-paper', methods=['POST'])
def concurrent_langchain():
    files = request.files.getlist('files')
    if not files:
        files = request.files.getlist('file')

    if not files: 
        return Response.error('No file part'), 400
    
    files = files[:10]
    size = request.form.get('size', 'medium')
    
    req_session_id = request.form.get('sessionId')
    if req_session_id in ['null', 'undefined', 'new', '']:
        req_session_id = None

    valid_files = []
    for file in files:
        file_content = file.read()
        if pdf_handler.validate_pdf(file_content, file.filename):
            valid_files.append((file_content, file.filename))

    if not valid_files:
        return Response.error('No valid PDF files found'), 400

    # 捕获 Flask 的应用上下文
    app = current_app._get_current_object()

    def process_and_save_single(content, fname, assigned_sid):
        """完全独立处理单文件：生成自己的 session_id、绑定数据库、并存入 Redis"""
        current_session_id = assigned_sid or str(uuid.uuid4())

        # 1. 独立的数据库映射绑定
        with app.app_context():
            try:
                file_hash = calculate_file_hash(content)
                paper = Paper.query.filter_by(file_hash=file_hash).first()
                if paper:
                    existing = SessionPaperMapping.query.filter_by(session_id=current_session_id, paper_id=paper.id).first()
                    if not existing:
                        mapping = SessionPaperMapping(session_id=current_session_id, paper_id=paper.id)
                        db.session.add(mapping)
                    db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Failed to create session_paper_mapping for {fname}: {str(e)}", exc_info=True)

        # 2. 调用大模型
        try:
            img_list = []
            for img in pdf_handler.convert_pdf_to_images(content):
                img_list.append(base64.b64encode(img).decode('utf-8'))
            
            full_text = ""
            for chunk in process_paper(img_list, size):
                full_text += chunk.content
            
            title = fname
            if 'Title:' in full_text:
                title_match = re.search(r'Title:\s*(.+)$', full_text, re.MULTILINE)
                if title_match: 
                    title = title_match.group(1).strip()
                    
            # 3. 独立存入 Redis（真正的：1份文件 = 1条独立聊天记录）
            if img_list and full_text:
                chat_manager = ChatContextManager()
                prompt = get_summary_prompt()
                user_content = [{"type": "text", "text": prompt['req'].format(size=size)}]
                user_content.extend([
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}} for img in img_list
                ])

                all_messages = [
                    [
                        {"role": "user", "content": user_content},
                        {"role": "assistant", "content": full_text}
                    ]
                ]
                chat_history = {"title": title, "messages": all_messages}
                chat_manager.add_history(current_session_id, chat_history, title)

            return current_session_id, full_text, title
        except Exception as e:
            logger.error(f"Error processing {fname}: {str(e)}", exc_info=True)
            return current_session_id, f"Error processing {fname}: {str(e)}", fname


    def generate_stream():
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = []
            for idx, (content, fname) in enumerate(valid_files):
                # 只有当请求中带有 sessionId 且确实只有一个文件时，才使用前端指定的 ID
                sid_to_assign = req_session_id if len(valid_files) == 1 and idx == 0 else None
                futures.append(executor.submit(process_and_save_single, content, fname, sid_to_assign))
            
            for i, future in enumerate(futures):
                try:
                    curr_sid, text, title = future.result()
                    # 推送自己的 SESSION_ID 回前端
                    if i == 0:
                        yield f"SESSION_ID:{curr_sid}\n"
                    
                    output_text = text
                    # (由于前端发起了3次独立请求，这里的 valid_files 恒为 1，不会再触发合并符)
                    if len(valid_files) > 1:
                        output_text = f"\n\n---\n**Document {i+1}: {title}**\n" + output_text
                    
                    yield output_text
                except Exception as e:
                    yield f"\nError: {str(e)}"

    return FlaskResponse(stream_with_context(generate_stream()), mimetype='text/event-stream')


@ocr_bp.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message')
    session_id = data.get('sessionId')

    if not session_id:
        return Response.error('No sessionId provided'), 400
    
    chat_manager = ChatContextManager()
    
    def generate():
        chain = get_chat_chain()
        history_msgs = chat_manager.get_history(session_id)
    
        full_response = ""
        for chunk in chain.stream({
            "history": history_msgs,
            "input": user_input
        }):
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            full_response += content
            yield content
    
        messages = [{"role": "user", "content": user_input}, {"role": "assistant", "content": full_response}]
        chat_manager.save_history(session_id, messages)
    
    return FlaskResponse(generate(), mimetype='text/event-stream')


@ocr_bp.route('/generate-review', methods=['POST'])
def generate_review():
    data = request.json
    session_ids = data.get('sessionIds', [])
    # 接收前端传来的文件夹名称
    folder_name = data.get('folderName') 
    
    if not session_ids or len(session_ids) == 0:
        return Response.error('No session IDs provided'), 400
        
    chat_manager = ChatContextManager()
    
    try:
        if folder_name and folder_name.strip():
            # 1. 创建新文件夹
            new_folder = Folder(name=folder_name.strip())
            db.session.add(new_folder)
            db.session.flush() # 获取新文件夹的 ID
            
            # 2. 根据 session_ids 去映射表中找出对应的 paper_ids
            # 利用 IN 查询和 set 去重，避免重复论文
            mappings = SessionPaperMapping.query.filter(SessionPaperMapping.session_id.in_(session_ids)).all()
            paper_ids = list(set([m.paper_id for m in mappings])) 
            
            # 3. 将找出的论文关联到新文件夹
            if paper_ids:
                papers = Paper.query.filter(Paper.id.in_(paper_ids)).all()
                new_folder.papers.extend(papers)
                
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to create folder and link papers: {str(e)}", exc_info=True)
        # 注意：这里只打印日志，不抛出500错误阻断主流程。即便文件夹创建失败，Review 依然会正常生成。

    # 组装 Prompt 数据
    summaries_text = ""
    valid_count = 0
    for sid in session_ids:
        summary_data = chat_manager.get_session_summary(sid)
        if summary_data and summary_data.get('summary'):
            valid_count += 1
            summaries_text += f"---\nPaper {valid_count}:\nTitle: {summary_data.get('title')}\nSummary: {summary_data.get('summary')}\n\n"
            
    if valid_count == 0:
        return Response.error('No valid summaries found'), 400
        
    user_prompt_text = f"Please write a literature review based on the following {valid_count} paper summaries:\n\n{summaries_text}\nNow, generate the Literature Review based ONLY on the provided summaries."

    # 生成一个专属于这篇综述的唯一 ID
    review_id = str(uuid.uuid4())

    def generate():
        # 1. 类似 chat，先向前端推送带有 ID 的头信息
        yield f"REVIEW_ID:{review_id}\n"
        
        full_text = ""
        try:
            for chunk in generate_literature_review_stream(user_prompt_text):
                content = chunk.content if hasattr(chunk, 'content') else str(chunk)
                full_text += content
                yield content

        except Exception as e:
            logger.error(f"Literature Review Generation error: {str(e)}", exc_info=True)
            yield f"\nError: {str(e)}"
            
        finally:
            # 2. 流式结束后，从 full_text 提取标题并保存
            if full_text.strip():
                title = "Untitled Literature Review"
                title_match = re.search(r'^Title:\s*(.+)$', full_text, re.MULTILINE)
                if title_match:
                    title = title_match.group(1).strip()
                    # 移除正文中的 Title 行
                    full_text = re.sub(r'^Title:\s*.+\n+', '', full_text, count=1)

            chat_manager.add_review(review_id, full_text, title)

    return FlaskResponse(generate(), mimetype='text/event-stream')


@ocr_bp.route('/reviews', methods=['GET'])
def get_all_reviews():
    chat_manager = ChatContextManager()
    reviews = chat_manager.get_all_reviews()
    return Response.success_with_data(message='Retrieve reviews successfully!', data=reviews)


@ocr_bp.route('/reviews/<review_id>', methods=['GET'])
def get_review_detail(review_id):
    chat_manager = ChatContextManager()
    content = chat_manager.get_review_detail(review_id)
    if not content:
        return Response.error('Review not found'), 404
    
    # 解析出标题返回
    title = chat_manager.get_review_title(review_id)

    return Response.success_with_data(message='Retrieve review successfully!', data={"id": review_id, "title": title, "content": content})


@ocr_bp.route('/reviews/batch-delete', methods=['POST'])
def batch_delete_reviews():
    data = request.json
    review_ids = data.get('reviewIds', [])
    chat_manager = ChatContextManager()
    for rid in review_ids:
        chat_manager.clear_review(rid)
    return Response.success("Deleted successfully")