from app.utils.get_config import get_openai_config
from app.utils.chat_manager import ChatContextManager
from flask import request, Blueprint
import openai
from app.constant.standard_response import Response


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
    return Response.success_with_data(message="Success", data=sessions)


@chat_bp.route('/session/<session_id>/summary', methods=['GET'])
def get_session_title(session_id):
    summary = chat_manager.get_session_summary(session_id)
    return Response.success_with_data(message="Success", data=summary)


@chat_bp.route('/session/<session_id>/messages', methods=['GET'])
def get_session_messages(session_id):
    page = int(request.args.get('page', 1))

    history = chat_manager.get_session_messages(session_id, page)
    return Response.success_with_data(message="Success", data=history)