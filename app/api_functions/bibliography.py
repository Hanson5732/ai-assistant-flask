from app.utils.get_prompts import get_metadata_prompt
from app.utils.get_config import get_ocr_config
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage


def get_model():
    config = get_ocr_config()
    return ChatOpenAI(
        model=config['model'],
        openai_api_key=config['ocr_api_key'],
        openai_api_base=config['ocr_base_url'],
        temperature=float(config['temperature']),
        streaming=False,
        max_tokens=int(config['max_token']),
    )

def extract_chain(pdf_imgs):
    llm = get_model()
    prompt = get_metadata_prompt()

    # 构建多模态消息内容
    content = [
        {"type": "text", "text": prompt}
    ]

    for img_bytes in pdf_imgs:
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_bytes}"}
        })

    message = HumanMessage(content=content)

    return llm.invoke([message]).content
