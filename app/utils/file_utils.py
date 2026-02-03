import oss2
import hashlib
from app.utils.get_config import get_oss_config

def upload_file(file_path, object):
    # read config
    config = get_oss_config()
    endpoint = f'https://oss-{config["region"]}.aliyuncs.com'

    # initial verification and bucket
    auth = oss2.Auth(config['access_key_id'], config['access_key_secret'])
    bucket = oss2.Bucket(auth, endpoint, config['bucket_name'])

    try:
        with open(file_path, 'rb') as file:
            bucket.put_object(object, file)
    except Exception as e:
        print(f'upload file failed: {e}')


def calculate_file_hash(file_stream):
    """
    计算文件的 SHA256 或 MD5 哈希值，用于查重
    """
    hash_func = hashlib.sha256()
    # 确保指针在文件开头
    file_stream.seek(0)
    # 分块读取，防止大文件占用过多内存
    for chunk in iter(lambda: file_stream.read(4096), b""):
        hash_func.update(chunk)
    # 重置指针，方便后续保存文件操作
    file_stream.seek(0)
    return hash_func.hexdigest()