from flask import Blueprint, request, jsonify
from app import db
from app.models.paper import Paper, Reference
from app.utils.file_utils import calculate_file_hash
from app.utils.pdf_handler import PDFHandler
from app.api_functions.bibliography import extract_chain
import json
from app.constant.standard_response import Response
from app.utils.file_utils import upload_file
import base64

bibli_bp = Blueprint('bibli_storage', __name__)
pdf_handler = PDFHandler()

@bibli_bp.route('/upload', methods=['POST'])
def upload_paper():
    file = request.files.get('file')

    if not file: return Response.error('No file part'), 400
    
    file_content = file.read()
    if not pdf_handler.validate_pdf(file_content, file.filename):
        return Response.error('Invalid PDF file'), 400

    # 1. 计算文件哈希进行查重
    file_hash = calculate_file_hash(file_content)
    existing_paper = Paper.query.filter_by(file_hash=file_hash).first()

    if existing_paper:
        # 如果数据库已存在，直接返回存储的元数据
        return Response.success_with_data(
            message = "File already exists, retrieved from database",
            data= {
                "id": existing_paper.id,
                "title": existing_paper.title,
                "authors": existing_paper.get_authors(),
                "pub_year": existing_paper.pub_year,
                "venue": existing_paper.venue,
                "doi": existing_paper.doi
            })

    
    try:
        pdf_imgs = []
        all_pages = list(pdf_handler.convert_pdf_to_images(file_content))

        # 第一页和最后三页
        selected_pages = all_pages[:1] + all_pages[-3:] if len(all_pages) > 4 else all_pages
        for img_bytes in selected_pages:
            pdf_imgs.append(base64.b64encode(img_bytes).decode('utf-8'))
        
        full_response = extract_chain(pdf_imgs).strip()
        if full_response.startswith("```json"):
            full_response = full_response.split("```json")[1].split("```")[0].strip()
        elif full_response.startswith("```"):
            full_response = full_response.split("```")[1].split("```")[0].strip()

        # 假设 LLM 返回的是标准 JSON 格式字符串
        metadata = json.loads(full_response)

        # 4. 保存文件物理路径
        file_url = upload_file(file_content)

        # 5. 元数据入库
        new_paper = Paper(
            file_hash=file_hash,
            title=metadata.get('title', file.filename),
            pub_year=metadata.get('pub_year'),
            venue=metadata.get('venue'),
            page_range=metadata.get('page_range'),
            doi=metadata.get('doi'),
            pdf_url=file_url
        )
        new_paper.set_authors(metadata.get('authors', []))
        
        db.session.add(new_paper)
        db.session.flush() # 获取生成的 paper_id

        # 6. 参考文献入库
        references = metadata.get('references', [])
        for idx, ref in enumerate(references):
            new_ref = Reference(
                paper_id=new_paper.id,
                # 如果 ref 是字典，需要取其中的字符串字段
                raw_text=ref.get('raw_text') if isinstance(ref, dict) else str(ref),
                formatted_title=ref.get('formatted_title') if isinstance(ref, dict) else None,
                order_num=idx + 1
            )
            db.session.add(new_ref)

        db.session.commit()

        return Response.success_with_data(
            message = "Upload and analysis successful",
            data= metadata
        )

    except Exception as e:
        import traceback
        traceback.print_exc() # 在控制台打印完整的堆栈信息
        db.session.rollback()
        return jsonify({"error": str(e)}), 500


@bibli_bp.route('/list', methods=['GET'])
def get_paper_list():
    """
    获取文献列表，按上传时间倒序排列
    """
    try:
        # 按上传时间倒序查询
        papers = Paper.query.order_by(Paper.upload_time.desc()).all()
        
        data = []
        for p in papers:
            # 处理作者列表：将 List 转为字符串 "Author1, Author2" 以便前端显示
            authors_list = p.get_authors()
            author_display = "Unknown"
            if authors_list:
                author_display = ", ".join(authors_list)
            
            data.append({
                "id": p.id,
                "title": p.title,
                "author": author_display,    # 对应前端 item.author
                "publish_date": str(p.pub_year) if p.pub_year else "N/A", # 对应前端 item.publish_date
                "venue": p.venue,
                "doi": p.doi
            })

        return Response.success_with_data(data=data, message="")

    except Exception as e:
        return Response.error(f"Access bibliography error: {str(e)}"), 500

    
@bibli_bp.route('/delete/<int:paper_id>', methods=['DELETE'])
def delete_paper(paper_id):
    """
    删除指定文献及其关联数据
    """
    try:
        paper = Paper.query.get(paper_id)
        if not paper:
            return Response.error("Bibliography not found"), 404

        # 由于在 models.py 中配置了 cascade="all, delete-orphan"
        # 删除 paper 会自动删除关联的 references
        db.session.delete(paper)
        db.session.commit()

        return Response.success(message="Delete success")

    except Exception as e:
        db.session.rollback()
        return Response.error(f"Delete failed: {str(e)}"), 500


@bibli_bp.route('/detail/<int:paper_id>', methods=['GET'])
def get_paper_detail(paper_id):
    try:
        paper = Paper.query.get(paper_id)
        if not paper:
            return Response.error("Paper not found"), 404
        
        # 格式化参考文献列表
        refs = []
        if paper.references:
            for ref in paper.references:
                refs.append({
                    "id": ref.id,
                    "text": ref.formatted_title or ref.raw_text,
                    "order": ref.order_num
                })

        data = {
            "id": paper.id,
            "title": paper.title,
            "authors": paper.get_authors(),
            "pub_year": paper.pub_year,
            "venue": paper.venue,
            "doi": paper.doi,
            "page_range": paper.page_range,
            "pdf_url": paper.pdf_url,
            "upload_time": paper.upload_time.strftime('%Y-%m-%d'),
            "references": refs
        }
        return Response.success_with_data(data=data, message="")
    except Exception as e:
        return Response.error(f"Get paper detail failed: {str(e)}"), 500
