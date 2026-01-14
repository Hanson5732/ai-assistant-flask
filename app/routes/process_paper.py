import base64
from flask import request, Blueprint
from app.utils import pdf_handler
from app.utils.pdf_handler import PDFHandler
from app.constant.standard_response import Response
from app.api_functions.contextual_QA import deepseek_ocr_api, generate_final_summary


ocr_bp = Blueprint('ocr', __name__)
pdf_handler = PDFHandler()

@ocr_bp.route('/api/process-paper', methods=['POST'])
def process_paper():
    file = request.files.get('file')
    size = request.form.get('size', 'medium')
    if not file:
        return Response.error('No file part'), 400

    file_content = file.read()
    if not pdf_handler.validate_pdf(file_content, file.filename):
        return Response.error('Invalid PDF file'), 400

    try:
        full_text = []

        for idx, img_bytes in enumerate(pdf_handler.convert_pdf_to_images(file_content)):
            # 编码为 base64 字符串
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # 调用 DeepSeek OCR API
            ocr_text = deepseek_ocr_api(img_base64)
            full_text.append(f'--- Page {idx+1} ---\n{ocr_text}')

        # 将全文拼接后，再调用一次 DeepSeek 进行最终总结
        final_summary = generate_final_summary('\n'.join(full_text), size)
        print(final_summary)
        return Response.success_with_data(
            message='Paper processed successfully', 
            data={
                "summary": final_summary,
                "page_count": len(full_text)
            })

    except Exception as e:
        return Response.error(f"error: {str(e)}"), 500
