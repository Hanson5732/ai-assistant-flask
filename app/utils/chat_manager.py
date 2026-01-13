import redis
import json
from app.utils.get_config import get_redis_config

class ChatContextManager:
    def __init__(self, expire=3600*24):
        redis_config = get_redis_config()
        self.redis = redis.StrictRedis(
            host=redis_config['host'], 
            port=redis_config['port'], 
            db=redis_config['db'], 
            password=redis_config['password'], 
            decode_responses=True)
        self.expire = expire

    def _get_key(self, session_id):
        return f"chat_history:{session_id}"

    def get_history(self, session_id):
        """获取指定会话的历史记录"""
        key = self._get_key(session_id)
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        # 如果是新会话，初始化 System Prompt
        return [{"role": "system", "content": "你是一个专业的学术助手。"}]


    def save_history(self, session_id, messages):
        """保存历史记录并刷新过期时间"""
        key = self._get_key(session_id)
        # 只保留最近 15 轮对话，防止 Token 溢出
        if len(messages) > 31:  # 1 system + 15 user + 15 assistant
            messages = [messages[0]] + messages[-30:]

        self.redis.setex(key, self.expire, json.dumps(messages))

    
    def clear_history(self, session_id):
        """清除历史记录"""
        self.redis.delete(self._get_key(session_id))