import os
import requests
import json

API_KEY = os.getenv("OPENROUTER_API_KEY")

DEFAULT_MODEL = "google/gemini-2.5-flash"
class OpenRouterClient:

    def __init__(self):
        self.url = "https://openrouter.ai/api/v1/chat/completions"
        self.is_configured = API_KEY is not None

    def ask(self, prompt):

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": DEFAULT_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        response = requests.post(
            self.url,
            headers=headers,
            json=data
        )

        result = response.json()

        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        else:
            return str(result)

    def chat_stream(self, messages, model=DEFAULT_MODEL):

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        response = requests.post(
            self.url,
            headers=headers,
            json=data,
            stream=True
        )

        for line in response.iter_lines():

            if line:

                decoded = line.decode("utf-8")

                if decoded.startswith("data: "):

                    chunk = decoded[6:]

                    if chunk == "[DONE]":
                        break

                    try:
                        parsed = json.loads(chunk)
                        delta = parsed["choices"][0]["delta"]
                        if "content" in delta:
                            yield delta["content"]
                    except Exception:
                        continue
