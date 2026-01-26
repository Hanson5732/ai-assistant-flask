from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.utils.get_config import get_openai_config
from app.utils.get_prompts import get_summary_prompt
from app.utils.chat_manager import ChatContextManager

def get_model():
    config = get_openai_config()
    return ChatOpenAI(
        model=config['model'],
        openai_api_key=config['api_key'],
        openai_api_base=config['base_url'],
        temperature=config['temperature'],
        max_tokens=config['max_tokens']
    )

def process_paper(img_list, size):
    llm = get_model()
    prompt_data = get_summary_prompt()

    # 构建多模态消息内容
    content = [
        {"type": "text", "text": prompt_data['req'].format(size=size)}
    ]

    for img_bytes in img_list:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_bytes}"}
        })
    
    message = HumanMessage(content=content)

    return llm.stream([message])


def get_chat_chain():
    config = get_openai_config()

    
    llm = ChatOpenAI(
        model="gemini-2.0-flash-free",
        openai_api_key=config['api_key'],
        openai_api_base=config['base_url']
    )

    # 构造包含历史记录的 Prompt
    prompt = ChatPromptTemplate.from_mesges([
        ("system", "你是一个论文分析助手。请基于上方提供的论文原文和之前的对话历史回答用户问题。"),
        MessagesPlaceholder(variable_name="history"),
        ("user", "{input}")
    ])

    return prompt | llm