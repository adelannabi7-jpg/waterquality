import os
import requests

API_KEY = os.getenv("OPENROUTER_API_KEY")

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
            "model": "poolside/laguna-m1-free",
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
