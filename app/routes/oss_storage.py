import uuid
import oss2
from app.utils.get_config import get_oss_config

# 获取配置并初始化 OSS Bucket
config = get_oss_config()
auth = oss2.Auth(config['access_key_id'], config['access_key_secret'])
bucket = oss2.Bucket(auth, config['region'], config['bucket_name'])

def upload_to_oss(file_data, file_name, folder="papers"):
    """
    通用上传函数
    :param file_data: 可以是文件流、字节数组或本地路径
    :param file_name: 文件名（包括扩展名）
    :param folder: 存储目录
    :return: 文件的访问 URL
    """
    # 生成唯一文件名防止覆盖
    unique_filename = f"{folder}/{uuid.uuid4()}_{file_name}"
    
    try:
        # 执行上传
        bucket.put_object(unique_filename, file_data)
        
        # 拼接访问 URL
        # 如果是私有库，这里可能需要生成带签名的 URL；如果是公共读，直接拼接即可
        url = f"https://{config['OSS_BUCKET_NAME']}.{config['OSS_ENDPOINT']}/{unique_filename}"
        return url
    except Exception as e:
        print(f"OSS Upload Error: {str(e)}")
        return None