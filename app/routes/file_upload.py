import oss2
from app.utils.oss_info_utils import get_oss_config

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