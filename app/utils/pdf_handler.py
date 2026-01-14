import os
import logging
import fitz
import io

logger = logging.getLogger(__name__)

class PDFHandler:
    def __init__(self):
        self.supported_extensions = ['.pdf', '.PDF']

    def validate_pdf(self, file_content: bytes, filename: str) -> bool:
        try:
            extension = os.path.splitext(filename)[1].lower()
            if extension not in self.supported_extensions:
                logger.error(f'file extension {extension} is not supported')
                return False

            file_size = len(file_content)
            
            if file_size > 20 * 1024 * 1024:  # 20MB
                logger.error(f"file size {file_size / 1024 / 1024:.2f}MB exceeds 20MB limit")
                return False

            return True
        
        except Exception as e:
            logger.error(f'validate pdf failed: {e}')
            return False

    @staticmethod
    def convert_pdf_to_images(file_stream: io.BytesIO, dpi=200):
        try:
            # 1. load pdf document
            doc = fitz.open(stream=file_stream, filetype='pdf')
            
            # 2. 严格按页码顺序遍历
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
            
                # 设置缩放比例 (DPI / 72.0)
                zoom = dpi / 72
                mat = fitz.Matrix(zoom, zoom)
            
                # 3. 将页面渲染为像素图 (Pixmap)
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            
                # 4. 转换为图片字节流 (以便直接发送给 DeepSeek 接口)
                img_bytes = pix.tobytes("jpg")
                
                yield img_bytes
        
            doc.close()
        except Exception as e:
            logger.error(f'PDF 渲染图片失败：{e}')
            raise