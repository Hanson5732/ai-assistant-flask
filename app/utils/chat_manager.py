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

    def save_paper_context(self, session_id, summary_text):
        """专门保存论文总结作为后续对话的持久背景"""
        key = f"paper_context:{session_id}"
        self.redis.setex(key, self.expire, summary_text)

    def get_history(self, session_id):
        """获取历史记录，并将论文背景注入到 System Message 中"""
        # 获取对话历史
        history_key = f"chat_history:{session_id}"
        data = self.redis.get(history_key)
        history = json.loads(data) if data else []

        # 获取论文背景
        context_key = f"paper_context:{session_id}"
        paper_summary = self.redis.get(context_key) or "未提供论文背景。"

        # 始终将最新的背景作为第一条 System Prompt
        system_prompt = f"你是一个专业的学术助手。以下是论文的分析背景：\n{paper_summary}"
        
        return [{"role": "system", "content": system_prompt}] + history

    def save_history(self, session_id, messages):
        """只保存用户和助手的对话部分，不重复保存 System Prompt"""
        key = f"chat_history:{session_id}"
        # 过滤掉 system 消息，只存 user 和 assistant 的对话
        chat_only = [m for m in messages if m['role'] != 'system']
        
        # 限制长度 (保留最近 20 条记录)
        if len(chat_only) > 20:
            chat_only = chat_only[-20:]

        self.redis.setex(key, self.expire, json.dumps(chat_only))

    
    def clear_history(self, session_id):
        """清除历史记录"""
        self.redis.delete(self._get_key(session_id))