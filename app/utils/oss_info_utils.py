import configparser

def get_oss_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    oss_config = config['oss']
    return {
        'access_key_id': oss_config.get('OSS_ACCESS_KEY_ID'),
        'access_key_secret': oss_config.get('OSS_ACCESS_KEY_SECRET'),
        'region': oss_config.get('OSS_REGION'),
        'bucket_name': oss_config.get('OSS_BUCKET_NAME')
    }