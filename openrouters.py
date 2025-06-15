import json
import os
import requests
from dotenv import load_dotenv


load_dotenv()
LLM_TOKEN = os.environ.get("LLM_TOKEN")
MODEL = os.environ.get("MODEL")

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

if __name__ == "__main__":
    pass
