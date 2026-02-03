from app import db
from datetime import datetime
import json

class Paper(db.Model):
    __tablename__ = 'papers'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    file_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    title = db.Column(db.String(512), nullable=False)
    authors = db.Column(db.Text)  # 存储 JSON 格式的作者列表字符串
    pub_year = db.Column(db.Integer)
    venue = db.Column(db.String(256)) # 期刊或会议
    doi = db.Column(db.String(128), index=True)
    pdf_url = db.Column(db.String(512)) # OSS或本地路径
    page_range = db.Column(db.String(64)) # 页码范围，如 "10-20"
    upload_time = db.Column(db.DateTime, default=datetime.now)

    # 建立与参考文献的一对多关系，cascade确保删除论文时自动删除参考文献
    references = db.relationship('Reference', backref='paper', cascade="all, delete-orphan", lazy=True)

    def set_authors(self, author_list):
        self.authors = json.dumps(author_list, ensure_ascii=False)

    def get_authors(self):
        return json.loads(self.authors) if self.authors else []

class Reference(db.Model):
    __tablename__ = 'references'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    paper_id = db.Column(db.Integer, db.ForeignKey('papers.id'), nullable=False)
    raw_text = db.Column(db.Text)
    formatted_title = db.Column(db.String(512))
    order_num = db.Column(db.Integer)

    def __repr__(self):
        return f'<Reference {self.formatted_title}>'