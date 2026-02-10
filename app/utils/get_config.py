import configparser


def get_oss_config():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    oss_config = config['oss']
    return {
        'access_key_id': oss_config.get('OSS_ACCESS_KEY_ID'),
        'access_key_secret': oss_config.get('OSS_ACCESS_KEY_SECRET'),
        'region': oss_config.get('OSS_REGION'),
        'bucket_name': oss_config.get('OSS_BUCKET_NAME')
    }


def get_openai_config():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    openai_config = config['openai']
    return {
        'api_key': openai_config.get('OPENAI_API_KEY'),
        'base_url': openai_config.get('BASE_URL'),
        'temperature': float(openai_config.get('TEMPERATURE')),
        'model': openai_config.get('MODEL')
    }


def get_redis_config():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    redis_config = config['redis']
    return {
        'host': redis_config.get('REDIS_HOST'),
        'port': int(redis_config.get('REDIS_PORT')),
        'db': int(redis_config.get('REDIS_DB')),
        'password': redis_config.get('REDIS_PASSWORD')
    }


def get_mysql_config():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    mysql_config = config['mysql']
    return {
        'host': mysql_config.get('MYSQL_HOST'),
        'port': int(mysql_config.get('MYSQL_PORT')),
        'user': mysql_config.get('MYSQL_USER'),
        'password': mysql_config.get('MYSQL_PASSWORD'),
        'database': mysql_config.get('MYSQL_DATABASE')
    }


def get_ocr_config():
    config = configparser.ConfigParser()
    config.read('config.ini', encoding='utf-8')
    ocr_config = config['ocr']
    return {
        'ocr_api_key': ocr_config.get('OCR_API_KEY'),
        'ocr_base_url': ocr_config.get('OCR_BASE_URL'),
        'model': ocr_config.get('MODEL'),
        'temperature': float(ocr_config.get('TEMPERATURE')),
        'max_token': int(ocr_config.get('MAX_TOKEN')),
    }