from flask import Blueprint, request
from app import db
from app.models.paper import Paper, Folder
from app.constant.standard_response import Response

folder_bp = Blueprint('folder', __name__)

@folder_bp.route('/create', methods=['POST'])
def create_folder():
    data = request.json
    name = data.get('name')
    if not name:
        return Response.error("Folder name is required"), 400
    
    new_folder = Folder(name=name)
    db.session.add(new_folder)
    db.session.commit()
    return Response.success(message="Folder created")

@folder_bp.route('/delete/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    folder = Folder.query.get(folder_id)
    if not folder:
        return Response.error("Folder not found"), 404
    db.session.delete(folder)
    db.session.commit()
    return Response.success(message="Folder deleted")

@folder_bp.route('/<int:folder_id>/papers', methods=['POST'])
def batch_update_papers(folder_id):
    """批量添加或剔除文献"""
    folder = Folder.query.get(folder_id)
    if not folder:
        return Response.error("Folder not found"), 404
        
    data = request.json
    action = data.get('action') # 'add' 或 'remove'
    paper_ids = data.get('paper_ids', [])
    
    papers = Paper.query.filter(Paper.id.in_(paper_ids)).all()
    
    if action == 'add':
        for p in papers:
            if p not in folder.papers:
                folder.papers.append(p)
    elif action == 'remove':
        for p in papers:
            if p in folder.papers:
                folder.papers.remove(p)
    else:
        return Response.error("Invalid action"), 400
        
    db.session.commit()
    return Response.success(message=f"Successfully {action}ed papers")

@folder_bp.route('/<int:folder_id>', methods=['GET'])
def get_folder_details(folder_id):
    """获取文件夹及其包含的所有文献"""
    folder = Folder.query.get(folder_id)
    if not folder:
         return Response.error("Folder not found"), 404
         
    papers_data = []
    for p in folder.papers:
        papers_data.append({
            "id": p.id,
            "title": p.title,
            "authors": p.get_authors(),
            "pub_year": p.pub_year,
            "venue": p.venue,
            "doi": p.doi,
            "page_range": p.page_range
        })
        
    return Response.success_with_data("Successfully get folder details", {
        "id": folder.id,
        "name": folder.name,
        "papers": papers_data
    })


@folder_bp.route('/list', methods=['GET'])
def get_folder_list():
    """获取所有文件夹列表"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 8

        pagination = Folder.query.order_by(Folder.create_time.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        folders = pagination.items
        data = []
        for f in folders:
            data.append({
                "id": f.id,
                "name": f.name,
                "paper_count": len(f.papers),
                "create_time": f.create_time.strftime('%Y-%m-%d')
            })
            
        # 返回类似 bibli/list 的分页结构
        return Response.success_with_data(message="Success", data={
            "list": data,
            "total": pagination.total,
            "pages": pagination.pages,
            "current_page": pagination.page
        })
    except Exception as e:
        return Response.error(f"Failed to get folders: {str(e)}"), 500