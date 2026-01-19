from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.get_config import get_openai_config
from app.utils.get_prompts import get_summary_prompt

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