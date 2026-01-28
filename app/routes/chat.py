from app.utils.get_config import get_openai_config
from app.utils.chat_manager import ChatContextManager
from flask import request, Blueprint
import openai
from app.constant.standard_response import Response
from app.api_functions.contextual_QA import get_chat_chain


chat_bp = Blueprint('chat', __name__)
openai_config = get_openai_config()
chat_manager = ChatContextManager()

client = openai.OpenAI(
    api_key=openai_config['api_key'],
    base_url=openai_config['base_url']
)


@chat_bp.route('/reset', methods=['POST'])
def reset_chat():
    session_id = request.json.get('session_id')
    chat_manager.clear_history(session_id)
    return Response.success("History cleared")


@chat_bp.route('/sessions', methods=['GET'])
def list_sessions():
    sessions = chat_manager.get_all_sessions()
    result = [
        {"id": sid, "title": title} 
        for sid, title in sessions.items()
    ]
    return Response.success_with_data(message="Success", data=result)


@chat_bp.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    history = chat_manager.get_session_detail(session_id)
    return Response.success_with_data(message="Success", data=history)