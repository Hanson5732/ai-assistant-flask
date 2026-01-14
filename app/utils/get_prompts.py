import configparser

def get_summary_prompt():
    config = configparser.ConfigParser()
    config.read('prompts.ini')
    summary_prompt = config['summary']
    return {
        'system_prompt': summary_prompt.get('SYSTEM_PROMPT'),
        'req': summary_prompt.get('REQ')
    }
    