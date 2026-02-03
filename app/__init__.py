from flask import Flask
from flask_cors import CORS
import logging
from flask_sqlalchemy import SQLAlchemy
from app.utils.get_config import get_mysql_config

db = SQLAlchemy()
def create_app():
    app = Flask(__name__)

    # 允许所有来源跨域
    CORS(app)
    # 配置特定来源
    # CORS(app, resources={r"/*": {"origins": ["http://localhost:3000"]}})

    # 配置日志格式和级别
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("app.log")
        ]
    )

    mysql_config = get_mysql_config()
    app.config['SQLALCHEMY_DATABASE_URI'] = (
        f'mysql+pymysql://{mysql_config["user"]}:{mysql_config["password"]}'
        f'@{mysql_config["host"]}:{mysql_config["port"]}/{mysql_config["database"]}'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    db.init_app(app)


    # 注册路由
    from app.routes.chat import chat_bp
    from app.routes.process_paper import ocr_bp
    from app.routes.bibli_storage import bibli_bp
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(ocr_bp, url_prefix='/api/ocr')
    app.register_blueprint(bibli_bp, url_prefix='/api/bibli')

    
    return app