import os
import logging
import fitz
import io
import pdfplumber

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
    def convert_pdf_to_images(file_stream: io.BytesIO, page_list=None, dpi=200):
        try:
            # 1. load pdf document
            doc = fitz.open(stream=file_stream, filetype='pdf')

            iter_list = range(len(doc))

            if page_list is not None:
                iter_list = page_list
            
            # 2. 严格按页码顺序遍历
            for page_num in iter_list:
                page = doc.load_page(page_num)
            
                # 设置缩放比例 (DPI / 72.0)
                zoom = dpi / 72
                mat = fitz.Matrix(zoom, zoom)
            
                # 3. 将页面渲染为像素图 (Pixmap)
                pix = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
            
                # 4. 转换为图片字节流
                img_bytes = pix.tobytes("jpg")
                
                yield img_bytes
        
            doc.close()
        except Exception as e:
            logger.error(f'PDF 渲染图片失败：{e}')
            raise

    @staticmethod
    def find_references_page(file_content):
        """
        从后往前搜索第一个包含 'References' 关键字的页码
        """
    
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            total_pages = len(pdf.pages)

            for i in range(total_pages - 1, -1, -1):
                text = pdf.pages[i].extract_text()
                if text and ("References" in text or "REFERENCES" in text):
                    return [num for num in range(i-total_pages, total_pages)]
        return None