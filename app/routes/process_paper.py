import base64
import uuid
import logging
from flask import request, Blueprint, Response as FlaskResponse
from app.utils.pdf_handler import PDFHandler
from app.constant.standard_response import Response
from app.utils.chat_manager import ChatContextManager
from app.api_functions.contextual_QA import process_paper, get_chat_chain

ocr_bp = Blueprint('ocr', __name__)
pdf_handler = PDFHandler()
logger = logging.getLogger(__name__)

@ocr_bp.route('/api/process-paper', methods=['POST'])
def concurrent_langchain():
    file = request.files.get('file')
    size = request.form.get('size', 'medium')
    session_id = request.form.get('sessionId')
    if not session_id or session_id == 'null' or session_id == 'undefined':
        session_id = str(uuid.uuid4())

    if not file: return Response.error('No file part'), 400
    
    file_content = file.read()
    if not pdf_handler.validate_pdf(file_content, file.filename):
        return Response.error('Invalid PDF file'), 400

    def generate_stream():
        chat_manager = ChatContextManager()
        yield f"SESSION_ID:{session_id}\n"

        try:
            # 1. 将 PDF 转换为图片并转为 base64
            img_list = []
            for img in pdf_handler.convert_pdf_to_images(file_content):
                img_list.append(base64.b64encode(img).decode('utf-8'))
            
            # 2. 调用 Gemini 多模态模型
            full_summary_text = ""
            for chunk in process_paper(img_list, size):
                content = chunk.content
                full_summary_text += content
                yield content

            # 3. 保存到 Redis 历史
            if full_summary_text:
                chat_manager.save_history(session_id, full_summary_text)

        except Exception as e:
            logger.error(f"Gemini Workflow error: {str(e)}", exc_info=True)
            yield f"Error: {str(e)}"

    return FlaskResponse(generate_stream(), mimetype='text/event-stream')


@ocr_bp.route('/api/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message')
    session_id = request.json.get('sessionId')

    if not session_id:
        return Response.error('No sessionId provided'), 400
    
    chat_manager = ChatContextManager()
    
    
    def generate():
        chain = get_chat_chain(session_id)
        history_msgs = chat_manager.get_history(session_id)
    
        full_response = ""
        for chunk in chain.stream({
            "history": history_msgs,
            "input": user_input
        }):
            # 如果 chunk 是消息对象，提取 content 内容
            content = chunk.content if hasattr(chunk, 'content') else str(chunk)
            full_response += content
            yield content
    
        # 更新历史记录
        history_msgs.append({"role": "user", "content": user_input})
        history_msgs.append({"role": "assistant", "content": full_response})
        chat_manager.save_paper_context(session_id, history_msgs)
    
    return FlaskResponse(generate(), mimetype='text/event-stream')