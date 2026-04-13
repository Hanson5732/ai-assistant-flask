import redis
import json
from app.utils.get_config import get_redis_config
import time

class ChatContextManager:
    def __init__(self, expire=3600*24*7):
        redis_config = get_redis_config()
        self.redis = redis.StrictRedis(
            host=redis_config['host'], 
            port=redis_config['port'], 
            db=redis_config['db'], 
            password=redis_config['password'])
        self.expire = expire

    def _get_key(self, session_id):
        return f"chat_history:{session_id}"

    def _get_session_key(self):
        return "chat_sessions_index"

    def _get_session_time_key(self):
        return "chat_sessions_time_index"

    def add_history(self, session_id, chat_history, title):
        """添加历史记录"""
        key = self._get_key(session_id)
        serialized_data = json.dumps(chat_history)
        self.redis.setex(key, self.expire, serialized_data)
        self.redis.zadd(self._get_session_time_key(), {session_id: time.time()})
        self.redis.hset(self._get_session_key(), session_id, title)


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
        data = json.loads(existing_data_json)
        data['messages'].extend(pairs)
        self.redis.setex(key, self.expire, json.dumps(data))
        self.redis.zadd(self._get_session_time_key(), {session_id: time.time()})


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
        self.redis.delete(f"chat_history:{session_id}")
        self.redis.zrem(self._get_session_time_key(), session_id)
        self.redis.hdel(self._get_session_key(), session_id)

    
    def get_all_sessions(self):
        """获取所有已存在的 session_id 列表"""
        session_ids = self.redis.zrevrange(self._get_session_time_key(), 0, -1)
        titles = self.redis.hgetall(self._get_session_key())
        
        result = []
        for sid in session_ids:
            sid_str = sid.decode('utf-8')
            raw_title = titles.get(sid, b"Unknown Session")
            title_str = raw_title.decode('utf-8', errors = 'ignore')
            result.append({
                "id": sid_str, 
                "title": title_str
            })

        return result


    def get_session_summary(self, session_id):
        """获取某个特定 session 的对话内容"""
        key = f"chat_history:{session_id}"
        raw_bytes = self.redis.get(key)
    
        if not raw_bytes:
            return None

        try:
            json_data = raw_bytes.decode('utf-8', errors='ignore')
            raw_data = json.loads(json_data)
            title = raw_data.get('title', 'Unkown title')

            messages_list = raw_data.get('messages', [])
            summary = ""

            if len(messages_list) > 0:
                summary = messages_list[0][1]['content'] if len(messages_list[0]) > 1 else ""

            return {
                "title": title, 
                "summary": summary
            }
        except Exception as e:
            print(f"解析 Session {session_id} 失败: {e}")
            return None


    def get_session_messages(self, session_id, page):
        key = f"chat_history:{session_id}"
        raw_bytes = self.redis.get(key)

        if not raw_bytes:
            return None

        try:
            json_data = raw_bytes.decode('utf-8', errors='ignore')
            raw_data = json.loads(json_data)

            messages_list = raw_data.get('messages', [])
            chat_messages = messages_list[1:]
            total_chat_len = len(chat_messages)

            limit = 3
            end = total_chat_len - ((page - 1) * limit)
            start = total_chat_len - (page * limit)

            if end <= 0:
                return {"messages": [], "more": False}

            actual_start = max(0, start)
            paginated_chat = chat_messages[actual_start:end]
            paginated_chat_reverse = paginated_chat[::-1]
            has_more = start > 0

            return {
                "messages": paginated_chat_reverse,
                "more": has_more
            }
        except Exception as e:
            print(f"解析 Session {session_id} 失败: {e}")
            return None

    
    def _get_review_key(self, review_id):
        return f"review_data:{review_id}"
    
    def _get_review_index_key(self):
        return "review_sessions_index"

    def _get_review_time_key(self):
        return "review_sessions_time_index"

    def add_review(self, review_id, content, title):
        """保存生成的文献综述全文"""
        key = self._get_review_key(review_id)
        # 半永久存储，过期时间同设为 expire (默认7天)
        self.redis.setex(key, self.expire, content)
        self.redis.zadd(self._get_review_time_key(), {review_id: time.time()})
        self.redis.hset(self._get_review_index_key(), review_id, title)

    def get_all_reviews(self):
        """获取所有已生成的文献综述列表"""
        review_ids = self.redis.zrevrange(self._get_review_time_key(), 0, -1)
        titles = self.redis.hgetall(self._get_review_index_key())
        
        result = []
        for rid in review_ids:
            rid_str = rid.decode('utf-8')
            raw_title = titles.get(rid, b"Untitled Literature Review")
            title_str = raw_title.decode('utf-8', errors='ignore')
            result.append({
                "id": rid_str, 
                "title": title_str
            })
        return result

    def get_review_detail(self, review_id):
        """获取某篇文献综述的详细内容"""
        key = self._get_review_key(review_id)
        raw_bytes = self.redis.get(key)
        if not raw_bytes:
            return None
        return raw_bytes.decode('utf-8', errors='ignore')

    def clear_review(self, review_id):
        """删除特定的文献综述"""
        self.redis.delete(self._get_review_key(review_id))
        self.redis.zrem(self._get_review_time_key(), review_id)
        self.redis.hdel(self._get_review_index_key(), review_id)

    def get_review_title(self, review_id):
        """从 Hash 索引中获取特定综述的标题"""
        raw_title = self.redis.hget(self._get_review_index_key(), review_id)
        if raw_title:
            return raw_title.decode('utf-8', errors='ignore')
        return "Untitled Literature Review"