import base64
import uuid
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from flask import request, Blueprint, Response as FlaskResponse

from app.utils.pdf_handler import PDFHandler
from app.constant.standard_response import Response
from app.utils.chat_manager import ChatContextManager
from app.api_functions.contextual_QA import process_paper, get_chat_chain
from app.utils.get_prompts import get_summary_prompt
from app.routes.literature_review import generate_literature_review_stream

ocr_bp = Blueprint('ocr', __name__)
pdf_handler = PDFHandler()
logger = logging.getLogger(__name__)


@ocr_bp.route('/process-paper', methods=['POST'])
def concurrent_langchain():
    # 接收前端传来的多个文件
    files = request.files.getlist('files')
    if not files:
        # 兼容处理：防范前端用了 'file' 作为键名
        files = request.files.getlist('file')

    if not files: 
        return Response.error('No file part'), 400
    
    # 强制限制最多 10 个文件
    files = files[:10]

    size = request.form.get('size', 'medium')
    session_id = request.form.get('sessionId')
    if not session_id or session_id == 'null' or session_id == 'undefined':
        session_id = str(uuid.uuid4())

    # 预先读取并校验文件
    valid_files = []
    for file in files:
        file_content = file.read()
        if pdf_handler.validate_pdf(file_content, file.filename):
            valid_files.append((file_content, file.filename))

    if not valid_files:
        return Response.error('No valid PDF files found'), 400

    def process_single_file(file_content, filename):
        """
        子线程内部任务：处理单个文件、转图片并请求大模型
        """
        try:
            img_list = []
            for img in pdf_handler.convert_pdf_to_images(file_content):
                img_list.append(base64.b64encode(img).decode('utf-8'))
            
            full_text = ""
            for chunk in process_paper(img_list, size):
                full_text += chunk.content
            
            title = filename
            if 'Title:' in full_text:
                title_match = re.search(r'Title:\s*(.+)$', full_text, re.MULTILINE)
                if title_match: 
                    title = title_match.group(1).strip()
                    
            return full_text, img_list, title
        except Exception as e:
            logger.error(f"Error processing {filename}: {str(e)}", exc_info=True)
            return f"Error processing {filename}: {str(e)}", [], filename


    def generate_stream():
        chat_manager = ChatContextManager()
        yield f"SESSION_ID:{session_id}\n"

        try:
            all_messages = []
            main_title = ""
            prompt = get_summary_prompt()

            # 使用线程池并发处理，限制并发数为 3
            with ThreadPoolExecutor(max_workers=3) as executor:
                # 按照上传的顺序依次提交任务
                futures = [
                    executor.submit(process_single_file, content, fname) 
                    for content, fname in valid_files
                ]
                
                # 按照原始顺序收取并推送结果（哪怕第3个文件先跑完，也会等待第1个文件先推送）
                for i, future in enumerate(futures):
                    full_summary_text, img_list, title = future.result()
                    
                    if i == 0:
                        main_title = title  # 采用第一个文件的标题作为 session 主标题

                    # 把内容推送给前端，若有多文件，利用分界线提升前端可读性
                    output_text = full_summary_text
                    if i > 0:
                        output_text = f"\n\n---\n**Document {i+1}: {title}**\n" + output_text
                    
                    yield output_text

                    # 保存到上下文记录中
                    if img_list:
                        user_content = [{"type": "text", "text": prompt['req'].format(size=size)}]
                        user_content.extend([
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}} for img in img_list
                        ])

                        all_messages.append([
                            {"role": "user", "content": user_content},
                            {"role": "assistant", "content": full_summary_text}
                        ])

            # 只有在有生成内容时，才统一保存到 Redis 历史
            if all_messages:
                chat_history = {"title": main_title or "Batch Summary", "messages": all_messages}
                chat_manager.add_history(session_id, chat_history, main_title or "Batch Summary")

        except Exception as e:
            logger.error(f"Gemini Batch Workflow error: {str(e)}", exc_info=True)
            yield f"\nError: {str(e)}"

    return FlaskResponse(generate_stream(), mimetype='text/event-stream')


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
    
    if not session_ids or len(session_ids) == 0:
        return Response.error('No session IDs provided'), 400
        
    chat_manager = ChatContextManager()
    
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
                
            # 2. 流式结束后，从 full_text 提取标题并保存
            title = "Untitled Literature Review"
            title_match = re.search(r'^Title:\s*(.+)$', full_text, re.MULTILINE)
            if title_match:
                title = title_match.group(1).strip()
                full_text = re.sub(r'^Title:\s*.+\n+', '', full_text, count=1)
                
            chat_manager.add_review(review_id, full_text, title)

        except Exception as e:
            logger.error(f"Literature Review Generation error: {str(e)}", exc_info=True)
            yield f"\nError: {str(e)}"
            
    return FlaskResponse(generate(), mimetype='text/event-stream')


@ocr_bp.route('/reviews', methods=['GET'])
def get_all_reviews():
    chat_manager = ChatContextManager()
    reviews = chat_manager.get_all_reviews()
    return Response.success(reviews)


@ocr_bp.route('/reviews/<review_id>', methods=['GET'])
def get_review_detail(review_id):
    chat_manager = ChatContextManager()
    content = chat_manager.get_review_detail(review_id)
    if not content:
        return Response.error('Review not found'), 404
    
    # 解析出标题返回
    title = "Untitled Literature Review"
    title_match = re.search(r'^Title:\s*(.+)$', content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

    return Response.success({"id": review_id, "title": title, "content": content})


@ocr_bp.route('/reviews/batch-delete', methods=['POST'])
def batch_delete_reviews():
    data = request.json
    review_ids = data.get('reviewIds', [])
    chat_manager = ChatContextManager()
    for rid in review_ids:
        chat_manager.clear_review(rid)
    return Response.success("Deleted successfully")