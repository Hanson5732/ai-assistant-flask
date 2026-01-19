import base64
import uuid
import logging
from flask import request, Blueprint, Response as FlaskResponse
from langchain_core.runnables import RunnableParallel, RunnableLambda
from app.utils.pdf_handler import PDFHandler
from app.constant.standard_response import Response
from app.utils.chat_manager import ChatContextManager
from app.utils.get_prompts import get_summary_prompt
from app.api_functions.contextual_QA import get_ocr_chain, get_summary_chain

ocr_bp = Blueprint('ocr', __name__)
pdf_handler = PDFHandler()
logger = logging.getLogger(__name__)

@ocr_bp.route('/api/concurrent', methods=['POST'])
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
            # 1. 准备图片数据
            img_list = list(pdf_handler.convert_pdf_to_images(file_content))
            
            # 2. 构建并行 OCR 任务字典
            # 使用 RunnableParallel 自动处理多线程并发
            ocr_chain = get_ocr_chain()
            parallel_ocr_tasks = {}
            for i, img in enumerate(img_list):
                img_b64 = base64.b64encode(img).decode('utf-8')
                # 为每一页创建一个独立的调用任务
                parallel_ocr_tasks[f"page_{i}"] = (
                    RunnableLambda(lambda x, b=img_b64: {"base64_img": b}) | ocr_chain
                )

            parallel_runnable = RunnableParallel(**parallel_ocr_tasks)
            
            # 3. 执行并行 OCR (LangChain 内部会使用线程池)
            # 这里的 config 可以设置 max_concurrency 限制并发数
            ocr_results = parallel_runnable.invoke({}, config={"max_concurrency": 10})

            # 4. 汇总文本
            
            full_paper_text = ""
            for i in range(len(img_list)):
                page_text = ocr_results.get(f"page_{i}", "[OCR Error]")
                full_paper_text += f"--- Page {i+1} ---\n{page_text}\n"

            # 5. 调用总结 Chain 并流式输出
            raw_prompt_data = get_summary_prompt()
            final_user_input = raw_prompt_data['req'].format(full_text=full_paper_text, size=size)
            summary_chain = get_summary_chain()
            full_summary_text = ""
            
            # stream 方法返回生成器
            for chunk in summary_chain.stream({"full_text": full_paper_text, "size": size}):
                full_summary_text += chunk
                yield chunk

            # 6. 保存历史
            if full_summary_text:
                history = chat_manager.get_history(session_id)
                history.append({"role": "system", "content": raw_prompt_data['system_prompt']})
                history.append({"role": "user", "content": final_user_input})
                history.append({"role": "assistant", "content": full_summary_text})
                chat_manager.save_history(session_id, history)

        except Exception as e:
            logger.error(f"LangChain Workflow error: {str(e)}", exc_info=True)
            yield f"Error: {str(e)}"

    return FlaskResponse(generate_stream(), mimetype='text/event-stream')