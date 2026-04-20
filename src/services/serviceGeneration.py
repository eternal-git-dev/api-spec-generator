import json
import os

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

        hints = config["generation_hints"]
        self.num_beams = hints["num_beams"]
        self.repetition_penalty = hints["repetition_penalty"]
        self.max_new_tokens = hints["max_new_tokens"]
        self.temperature = hints["temperature"]
        self.top_p = hints["top_p"]
        self.do_sample = hints.get("do_sample", False)

        self.few_shot_limit = hints.get("few_shot_limit")

        self._local = None
        self._remote = None

    @property
    def local(self):
        if self._local is None:
            self._local = Local(
                self.repetition_penalty, self.max_new_tokens, self.temperature,
                self.top_p, self.num_beams, self.do_sample,
            )
        return self._local

    @property
    def remote(self):
        if self._remote is None:
            self._remote = Remote(
                self.repetition_penalty, self.max_new_tokens, self.temperature,
                self.top_p, self.num_beams, self.do_sample,
            )
        return self._remote

    def _isRemoteEnabled(self):
        try:
            return bool(self.remote.is_requests_remaining())
        except Exception:
            return False

    def _select_engine(self):
        if self.mode == "local":
            return self.local
        if self.mode == "remote":
            return self.remote
        return self.remote if self._isRemoteEnabled() else self.local

    def generate(self, input):
        gen = self._select_engine()
        prompt = self._build_prompt(input)
        result = gen.generate(prompt)
        if not result:
            print('Ошибка при генерации ответа.')
            return None
        return result

    def _build_prompt(self, input):
        messages = [self.system, self.user]

        few_shot = self.few_shot
        if self.few_shot_limit is not None:
            few_shot = few_shot[: self.few_shot_limit]

        for ex in few_shot:
            messages.append(ex["user"])
            messages.append(ex["assistant"])

        messages.append({
            "role": "user",
            "content": "Вот компактный список эндпоинтов:\n" + str(input),
        })
        return messages