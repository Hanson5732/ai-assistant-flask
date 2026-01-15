import configparser

def get_summary_prompt():
    config = configparser.ConfigParser(delimiters=('='), interpolation=None)
    config.read('prompts.ini', encoding='utf-8')
    summary_prompt = config['summary']
    return {
        'system_prompt': summary_prompt.get('SYSTEM_PROMPT'),
        'req': summary_prompt.get('REQ')
    }
    