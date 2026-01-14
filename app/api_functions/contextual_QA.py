import openai
from app.utils.get_config import get_openai_config
from app.utils.get_prompts import get_summary_prompt

def deepseek_ocr_api(base64_img: str):
    openai_config = get_openai_config()
    client = openai.OpenAI(
        api_key=openai_config['api_key'],
        base_url=openai_config['base_url']
    )

    response = client.chat.completions.create(
        model="deepseek-ocr",
        messages=[{
            "role": "user", 
            "content": [
                { "type": "text", "text": "请识别这张论文图片中的文字，保持排版逻辑" },
                { "type": "image_url", "image_url": { "url": f"data:image/jpeg;base64,{base64_img}" } }
            ]
        }]
    )

    return response.choices[0].message.content


def generate_final_summary(full_text: str, size: str):
    if size not in ['small', 'medium', 'large']:
        size = 'medium'
    
    openai_config = get_openai_config()
    client = openai.OpenAI(
        api_key=openai_config['api_key'],
        base_url=openai_config['base_url']
    )

    summary_prompt = get_summary_prompt()
    summary_prompt['req'] = summary_prompt['req'].format(full_text=full_text, size=size)

    response = client.chat.completions.create(
        model="deepseek-v3.2",
        temperature=0.1,
        messages=[{
            "role": "system", 
            "content": summary_prompt['system_prompt']
        },
        {
            "role": "user", 
            "content": summary_prompt['req']
        }]
    )

    return response.choices[0].message.content