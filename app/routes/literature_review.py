from langchain_openai import ChatOpenAI
from app.utils.get_config import get_review_config
from app.utils.get_prompts import get_review_system_prompt

def get_model():
    config = get_review_config()
    return ChatOpenAI(
        model=config['model'],
        openai_api_key=config['review_api_key'],
        openai_api_base=config['review_base_url'],
        temperature=float(config['temperature']),
        streaming=False,
        max_tokens=int(config['max_token']),
    )


def generate_literature_review_stream(user_prompt_text):
    """
    根据组装好的用户 Prompt 生成文献综述（流式返回）
    """
    llm = get_model()
    system_prompt = get_review_system_prompt()

    chain = prompt | llm
    return chain.stream({'input': user_prompt_text})