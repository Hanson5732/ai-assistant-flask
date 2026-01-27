import redis
import json
from app.utils.get_config import get_redis_config

class ChatContextManager:
    def __init__(self, expire=3600*24*7):
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

    def _get_index_key(self):
        return "chat_sessions_index"

    def add_history(self, session_id, chat_history):
        """添加历史记录"""
        key = self._get_key(session_id)
        serialized_data = json.dumps(chat_history)
        self.redis.setex(key, self.expire, serialized_data)
        self.redis.sadd(self._get_index_key(), session_id)


    def save_history(self, session_id, messages):
        """专门保存论文总结作为后续对话的持久背景"""
        key = f"chat_history:{session_id}"
        chat_only = [m for m in messages if isinstance(m, dict) and m.get('role') != 'system']

        pairs = []
        for i in range(0, len(chat_only), 2):
            if i + 1 < len(chat_only):
                pairs.append([chat_only[i], chat_only[i+1]])
            else:
                pairs.append([chat_only[i]])

        existing_data_json = self.redis.get(key)
        data = json.load(existing_data_json)
        data['messages'].extend(pairs)
        self.redis.setex(key, self.expire, json.dumps(data))


    def get_history(self, session_id):
        """获取历史记录，并将论文背景注入到 System Message 中"""
        # 获取对话历史
        history_key = f"chat_history:{session_id}"
        data = self.redis.get(history_key)
        history = json.loads(data) if data else []
        raw_messages = history['messages']
        messages = []
        for pair in raw_messages:
            if len(pair) == 2:
                messages.extend(pair)
            else:
                messages.append(pair[0])

        return messages

    
    def clear_history(self, session_id):
        """清除历史记录"""
        self.redis.delete(self._get_key(session_id))

    
    def get_all_sessions(self):
        """获取所有已存在的 session_id 列表"""
        return self.redis.smembers(self._get_index_key())


    def get_session_detail(self, session_id):
        """获取某个特定 session 的对话内容"""
        key = f"chat_history:{session_id}"
        data = self.redis.get(key)
        return json.loads(data) if data else []