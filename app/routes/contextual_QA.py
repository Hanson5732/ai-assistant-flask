import openai

def contextual_qa():
    client = openai.OpenAI(
        api_key="sk-TDuX0idSBJLBdFf1Bc717253DdB643499eB38b5bEdF7A6Ef",
        base_url="https://aihubmix.com/v1"
    )

    response = client.chat.completions.create(
        model="deepseek-v3.2",
        messages=[{
            "role": "user", 
            "content": "Hello, how are you?"
            }]
    )

    print(response.choices[0].message.content)