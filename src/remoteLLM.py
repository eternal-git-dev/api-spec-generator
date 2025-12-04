import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

class Remote():
    def __init__(self, repetition_penalty, max_new_tokens, temperature, top_p, num_beams, do_sample):
        self.repetition_penalty = repetition_penalty
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.num_beams = num_beams
        self.do_sample = do_sample

        self.key = os.getenv("API_KEY")

    def _send_request(self, request: dict):
        response = requests.request(method=request["method"], url=request["url"], json=request.get('json'),
                                    headers=request["headers"])
        content = response.json()
        return content

    def generate(self, prompt) -> str | None:
        data = {
            "model": "amazon/nova-2-lite-v1:free",
            'messages': prompt,
            'max_tokens': self.max_new_tokens,
        }

        request = {
            "method": "POST",
            "url": "https://openrouter.ai/api/v1/chat/completions",
            "headers": {
                "Authorization": f"Bearer {self.key}",
                'Content-Type': 'application/json'
            },
            "json": data,
        }
        response = self._send_request(request)

        if not response:
            return None
        choices = response.get("choices", None)

        if not choices:
            print('Ошибка возврата LLM: ', json.dumps(prompt, indent=2, ensure_ascii=False))
            return None


        message = choices[0]["message"]['content']
        return message if len(message) > 0 else None

    def get_limits(self) -> dict | None:
        request = {
            "method": "GET",
            "url": "https://openrouter.ai/api/v1/key",
            "headers": {"Authorization": f"Bearer {self.key}"},
        }
        response = self._send_request(request)
        return response if response else None

    def is_requests_remaining(self) -> bool:
        limits = self.get_limits()
        remaining = limits.get('data').get('limit_remaining')
        if not remaining:
            return True
        return True if remaining > 0 else False
