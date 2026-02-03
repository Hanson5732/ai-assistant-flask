from langchain_core.messages import HumanMessage
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.utils.get_config import get_openai_config
from app.utils.get_prompts import get_summary_prompt


def get_model():
    config = get_openai_config()
    return ChatOpenAI(
        model=config['model'],
        openai_api_key=config['api_key'],
        openai_api_base=config['base_url'],
        temperature=config['temperature']
    )


def process_paper(img_list, size):
    if size == 'small':
        max_tokens = 512
    elif size == 'medium':
        max_tokens = 1024
    else:
        max_tokens = 2048

    llm = get_model()
    llm.max_tokens = max_tokens
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
        model="gemini-2.5-flash",
        openai_api_key=config['api_key'],
        openai_api_base=config['base_url']
    )

    # 构造包含历史记录的 Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a thesis analysis assistant. Please answer the user's questions based on the original thesis image provided above and the previous conversation history."),
        MessagesPlaceholder(variable_name="history"),
        ("user", "{input}")
    ])

    return prompt | llm