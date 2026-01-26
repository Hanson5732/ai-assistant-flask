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
    return Response.success_with_data(message="Success", data=list(sessions))


@chat_bp.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    history = chat_manager.get_session_detail(session_id)
    return Response.success_with_data(message="Success", data=history)


@chat_bp.route('/api/chat-stream', methods=['POST'])
def contextual_chat():
    data = request.json
    session_id = data.get('sessionId')
    user_input = data.get('message')

    if not session_id or not user_input:
        return Response.error("Missing data"), 400

    # 1. 获取 LangChain 组合好的 Prompt 链
    chain = get_chat_chain()
    
    def generate():
        full_answer = ""
        # 2. 从 Redis 获取历史记录传入 chain
        # 注意：get_history 已经处理了 System Message 的注入
        history_for_chain = chat_manager.get_history(session_id)
        
        # 3. 执行流式调用
        for chunk in chain.stream({"input": user_input, "history": history_for_chain}):
            content = chunk.content
            full_answer += content
            yield content
        
        # 4. 对话结束后，手动更新 Redis 里的历史记录
        # 我们只存用户输入和 AI 完整回复
        history_for_chain.append({"role": "user", "content": user_input})
        history_for_chain.append({"role": "assistant", "content": full_answer})
        chat_manager.save_history(session_id, history_for_chain)

    return FlaskResponse(generate(), mimetype='text/event-stream')