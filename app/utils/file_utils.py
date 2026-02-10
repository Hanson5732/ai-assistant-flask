import oss2
import hashlib
import uuid
from app.utils.get_config import get_oss_config

# read config
config = get_oss_config()
endpoint = f'https://oss-{config["region"]}.aliyuncs.com'
auth = oss2.Auth(config['access_key_id'], config['access_key_secret'])
bucket = oss2.Bucket(auth, endpoint, config['bucket_name'])


def upload_file(file_content, folder='papers'):

    # initial verification and bucket
    unique_filename = f"{folder}/{uuid.uuid4()}.pdf"

    url = f"https://{config['bucket_name']}.oss-{config['region']}.aliyuncs.com/{unique_filename}"

    try:
        bucket.put_object(unique_filename, file_content)
        return url
    except Exception as e:
        print(f'upload file failed: {e}')


def download_file(file_url):
    """
    从 OSS 下载文件
    """
    try:
        # 从 URL 提取文件名
        filename = file_url.split('/')[-1]
        # 下载文件到本地
        bucket.get_object_to_file(filename, filename)
        return filename
    except Exception as e:
        print(f"download file failed: {e}")
        return None


def calculate_file_hash(file_stream):
    """
    计算文件的 SHA256 或 MD5 哈希值，用于查重
    """
    hash_func = hashlib.sha256()

    if isinstance(file_stream, bytes):
        hash_func.update(file_stream)
    else:
        # 确保指针在文件开头
        file_stream.seek(0)
        # 分块读取，防止大文件占用过多内存
        for chunk in iter(lambda: file_stream.read(4096), b""):
            hash_func.update(chunk)
        # 重置指针，方便后续保存文件操作
        file_stream.seek(0)
    return hash_func.hexdigest()