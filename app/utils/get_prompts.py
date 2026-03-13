import configparser

def get_summary_prompt():
    config = configparser.ConfigParser(delimiters=('='), interpolation=None)
    config.read('prompts.ini', encoding='utf-8')
    summary_prompt = config['summary']
    return {
        'system_prompt': summary_prompt.get('SYSTEM_PROMPT'),
        'req': summary_prompt.get('REQ')
    }
    

def get_metadata_prompt():
    config = configparser.ConfigParser(delimiters=('='), interpolation=None)
    config.read('prompts.ini', encoding='utf-8')
    metadata_prompt = config['extract_metadata']
    return metadata_prompt.get('PROMPT')


def get_review_system_prompt():
    config = configparser.ConfigParser(delimiters=('='), interpolation=None)
    config.read('prompts.init', encoding='utf-8')
    system_prompt = config['literature_review_system']
    return system_prompt.get('PROMPT')


def get_review_user_prompt():
    config = configparser.ConfigParser(delimiters=('='), interpolation=None)
    config.read('prompts.init', encoding='utf-8')
    system_prompt = config['literature_review_user']
    return system_prompt.get('PROMPT')