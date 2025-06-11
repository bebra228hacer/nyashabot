import aiohttp
import asyncio
import json
import aiogram
import os
import requests
from dotenv import load_dotenv


load_dotenv()
LLM_TOKEN = os.environ.get("LLM_TOKEN")
MODEL = "deepseek/deepseek-r1"


class SmartMessage:
    def __init__(self):
        self.chat_id = ""
        self.message_id = message

    async def __call__(self, user_message_text, answer_message_id):
        self.prompt = user_message_text
        self.answer_message_id = answer_message_id


def process_content(content):
    return content.replace("<think>", "").replace("</think>", "")


def chat_stream(prompt):
    headers = {
        "Authorization": f"Bearer {LLM_TOKEN}",
        "Content-Type": "application/json",
    }

    data = {
        "model": MODEL,
        "messages": prompt,
        "stream": True,
    }

    with requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        json=data,
        stream=False,
    ) as response:
        if response.status_code != 200:
            print("Ошибка API:", response.status_code)
            return ""

        full_response = []

        for chunk in response.iter_lines():
            if chunk:
                chunk_str = chunk.decode("utf-8").replace("data: ", "")
                try:
                    chunk_json = json.loads(chunk_str)
                    if "choices" in chunk_json:
                        content = chunk_json["choices"][0]["delta"].get("content", "")
                        if content:
                            cleaned = process_content(content)
                            print(cleaned, end="", flush=True)
                            full_response.append(cleaned)
                except:
                    pass
        return "".join(full_response)


def send_request_to_openrouter1(
    prompt,
    model=MODEL,
    api_key=LLM_TOKEN,
):
    url = "https://api.openrouter.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    data = {"model": model, "messages": [{"role": "user", "content": prompt}]}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        response_json = response.json()
        # print(response_json) #Useful for debugging
        if "choices" in response_json and len(response_json["choices"]) > 0:
            return response_json["choices"][0]["message"]["content"]
        else:
            print("No choices returned in the response.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error sending request to OpenRouter: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None


def main():
    print("Чат с DeepSeek-R1 (by Antric)\nДля выхода введите 'exit'\n")

    while True:
        user_input = input("Вы: ")

        if user_input.lower() == "exit":
            print("Завершение работы...")
            break

        print("DeepSeek-R1:", end=" ", flush=True)
        chat_stream(user_input)

def send_request_to_openrouter(
    prompt,
    model=MODEL,
    api_key=LLM_TOKEN,
):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    data = {"model": model, "messages": prompt}

    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status() 

        response_json = response.json()
        print(response_json)
        if "choices" in response_json and len(response_json["choices"]) > 0:
            return response_json["choices"][0]["message"]["content"]
        else:
            print("No choices returned in the response.")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error sending request to OpenRouter: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None


# Example Usage:
if __name__ == "__main__":
    my_prompt = "What is the capital of France?"
    api_key = LLM_TOKEN  # Replace with your actual API key!

    response = send_request_to_openrouter(my_prompt, api_key=api_key)

    if response:
        print("Response:", response)
    else:
        print("Failed to get a response from OpenRouter.")
