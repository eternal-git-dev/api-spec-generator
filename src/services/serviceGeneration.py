import json
import os
import time

from localLLM import Local
from remoteLLM import Remote

class GenerationService:
    def __init__(self, mode: str):
        file_path = os.path.abspath(__file__)
        root_path = os.path.dirname(os.path.dirname(os.path.dirname(file_path)))
        config_path = os.path.join(root_path, 'config', 'cfg.json')

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        self.prompt_settings = config['prompt_settings']
        self.mode = mode
        self.system = self.prompt_settings["system"]
        self.user = self.prompt_settings["user"]
        self.few_shot = self.prompt_settings["few_shot"]

        self.num_beams = config["generation_hints"]["num_beams"]
        self.repetition_penalty = config["generation_hints"]["repetition_penalty"]
        self.max_new_tokens = config["generation_hints"]["max_new_tokens"]
        self.temperature = config["generation_hints"]["temperature"]
        self.top_p = config["generation_hints"]["top_p"]

        self.do_sample = True

        self.local = Local(self.repetition_penalty, self.max_new_tokens, self.temperature, self.top_p, self.num_beams, self.do_sample)
        self.remote = Remote(self.repetition_penalty, self.max_new_tokens, self.temperature, self.top_p, self.num_beams, self.do_sample)

    def _isRemoteEnabled(self):
        return True if self.remote.is_requests_remaining() else False

    def _select_engine(self):
        if self.mode == "local":
            return self.local
        elif self.mode == "remote":
            return self.remote
        return self.remote if self._isRemoteEnabled else self.local

    def generate(self, input):
        gen = self._select_engine()
        prompt = self._build_prompt(input)
        result = gen.generate(prompt)
        if not result:
            print('--------------------------')
            print('Ошибка при генерации ответа.')
            print(input)
            print('--------------------------')
            time.sleep(5)
        return result

    def _build_prompt(self, input):
        messages = []
        messages.append(self.system)
        messages.append(self.user)
        for ex in self.few_shot:
            messages.append(ex["user"])
            messages.append(ex["assistant"])

        messages.append({"role": "user", "content": "Вот компактный список эндпоинтов:\n" + str(input)})
        return messages
