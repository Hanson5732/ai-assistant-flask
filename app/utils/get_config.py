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

def get_openai_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    openai_config = config['openai']
    return {
        'api_key': openai_config.get('OPENAI_API_KEY'),
        'base_url': openai_config.get('BASE_URL')
    }


def get_redis_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    redis_config = config['redis']
    return {
        'host': redis_config.get('REDIS_HOST'),
        'port': int(redis_config.get('REDIS_PORT')),
        'db': int(redis_config.get('REDIS_DB')),
        'password': redis_config.get('REDIS_PASSWORD')
    }