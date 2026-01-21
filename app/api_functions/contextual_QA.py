from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from app.utils.get_config import get_openai_config
from app.utils.get_prompts import get_summary_prompt
from app.utils.chat_manager import ChatContextManager

def get_ocr_chain():
    config = get_openai_config()
    # 实例化 OCR 模型
    llm = ChatOpenAI(
        model="deepseek-ocr",
        openai_api_key=config['api_key'],
        openai_api_base=config['base_url']
    )
    
    # 定义 OCR Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("user", [
            {"type": "text", "text": "请识别这张论文图片中的文字，保持排版逻辑"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{base64_img}"}}
        ])
    ])
    
    return prompt | llm | StrOutputParser()

def get_summary_chain():
    config = get_openai_config()
    # 实例化总结模型
    llm = ChatOpenAI(
        model="deepseek-v3.2",
        openai_api_key=config['api_key'],
        openai_api_base=config['base_url'],
        temperature=0.1,
        streaming=True
    )
    
    prompt_data = get_summary_prompt()
    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_data['system_prompt']),
        ("user", prompt_data['req'])
    ])
    
    return prompt | llm | StrOutputParser()


def get_chat_chain(session_id: str):
    config = get_openai_config()
    chat_manager = ChatContextManager()
    
    # 获取之前存入的“论文+总结”历史
    existing_history = chat_manager.get_history(session_id)
    
    llm = ChatOpenAI(
        model="deepseek-v3.2",
        openai_api_key=config['api_key'],
        openai_api_base=config['base_url']
    )

    # 构造包含历史记录的 Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个论文分析助手。请基于上方提供的论文原文和之前的对话历史回答用户问题。"),
        MessagesPlaceholder(variable_name="history"),
        ("user", "{input}")
    ])

    return prompt | llm