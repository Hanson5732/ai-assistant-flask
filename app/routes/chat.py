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


@chat_bp.route('', methods=['POST'])
def chat_with_redis_context():
    data=request.json
    session_id = data.get('session_id')
    user_input = data.get('content')

    if not session_id or not user_input:
        return Response.error("Missing session_id or content"), 400

    try:
        # 1. 从 Redis 读取历史记录
        history = chat_manager.get_history(session_id)

        # 2. 加入用户当前提问
        history.append({"role": "user", "content": user_input})

        # 3. 调用 AI 模型
        response = client.chat.completions.create(
            model="deepseek-V3.2",
            messages=history
        )

        ai_message = response.choices[0].message.content

        # 4. 将 AI 回复加入历史并同步回 Redis
        history.append({'role': 'assistant', 'content': ai_message})
        chat_manager.save_history(session_id, history)

        return Response.success_with_data(
            message='',
            data={
                "answer": ai_message,
                "session_id": session_id
            }
        )

    except Exception as e:
        return Response.error(f"error: {str(e)}"), 500


@chat_bp.route('/reset', methods=['POST'])
def reset_chat():
    session_id = request.json.get('session_id')
    chat_manager.clear_history(session_id)
    return Response.success("History cleared")