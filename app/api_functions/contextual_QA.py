import openai
from app.utils.get_config import get_openai_config

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
    
    req=''
    if size == 'small':
        req = '5. 总结的长度在5-8句话'
    elif size == 'medium':
        req = '5. 总结的长度在10-15句话，中间对发现的新问题或提出的新方法、及实验结果作5-8句话描述'
    elif size == 'large':
        req = '5. 总结包含论文研究的原因、发现的新问题或提出的新方法、实验及结果、作者最后的总结作详细的描述'

    
    openai_config = get_openai_config()
    client = openai.OpenAI(
        api_key=openai_config['api_key'],
        base_url=openai_config['base_url']
    )

    response = client.chat.completions.create(
        model="deepseek-V3.2",
        messages=[{
            "role": "user", 
            "content": [
                { 
                    "type": "text", 
                    "text": f"""
                    请对以下论文内容进行总结，要求：
                    1. 保持逻辑连贯性
                    2. 提取主要内容
                    3. 保持原文的排版逻辑
                    4. 使用英文进行总结
                    {req}
                    """ 
                },
                { "type": "text", "text": full_text }
            ]
        }]
    )

    return response.choices[0].message.content