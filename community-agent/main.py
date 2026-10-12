import json

response_text = '''
{
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "你好，我是社区助手。"
            }
        }
    ]
}
'''
result = json.loads(response_text)
print(result["choices"][0]["message"]["content"])
