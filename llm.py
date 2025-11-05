import os
import json
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch


class LLM():
    def __init__(self):
        file_path = os.path.abspath(__file__)
        root_path = os.path.dirname(file_path)
        config_path = os.path.join(root_path, 'config', 'cfg.json')
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        self.system = config["system"]
        self.user = config["user"]
        self.few_shot = config["few_shot"]

        self.num_beams = config["generation_hints"]["num_beams"]
        self.repetition_penalty = config["generation_hints"]["repetition_penalty"]
        self.max_new_tokens = config["generation_hints"]["max_new_tokens"]
        self.temperature = config["generation_hints"]["temperature"]
        self.top_p = config["generation_hints"]["top_p"]
        self.do_sample = True
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.checkpoint = "HuggingFaceTB/SmolLM2-1.7B-Instruct"
        self.tokenizer = AutoTokenizer.from_pretrained(self.checkpoint)
        self.model = AutoModelForCausalLM.from_pretrained(self.checkpoint).to(self.device)

    def _build_prompt(self, input):
        prompt = []

        prompt.append(self.system.strip())

        for ex in self.few_shot:
            inp = json.dumps(ex["input"], ensure_ascii=False)
            out = ex["output"].strip()
            prompt.append(f"Пример входа: {inp}")
            prompt.append(f"Пример выхода: {out}")

        prompt.append(f"Вход: {input}")
        prompt.append("Выход:")

        return "\n\n".join(prompt)


    def generate(self, input):
        prompt = self._build_prompt(input)
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=2048
        ).to(self.device)

        input_len = inputs["input_ids"].shape[1]
        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                repetition_penalty=self.repetition_penalty,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                top_p=self.top_p,
                num_beams=self.num_beams,
                do_sample=self.do_sample,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        generated_ids = outputs[0, input_len:]
        generated_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return generated_text
