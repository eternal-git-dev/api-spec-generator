import os
import json
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch


class LocalLLM():
    def __init__(self, repetition_penalty, max_new_tokens, temperature, top_p, num_beams, do_sample):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.num_beams = num_beams
        self.repetition_penalty = repetition_penalty
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.do_sample = do_sample

        self.checkpoint = "HuggingFaceTB/SmolLM2-1.7B-Instruct"
        self.tokenizer = AutoTokenizer.from_pretrained(self.checkpoint)
        self.model = AutoModelForCausalLM.from_pretrained(self.checkpoint).to(self.device)

        self.gen_kwargs = dict(
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=do_sample,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id
        )

    def generate(self, messages):
        text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=2048).to(self.device)
        input_len = inputs["input_ids"].shape[1]

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=False,
            num_beams=2,
            repetition_penalty=1.1,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id
        )

        #raw = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        gen_ids = outputs[0, input_len:]
        gen_text = self.tokenizer.decode(gen_ids, skip_special_tokens=True)
        return gen_text
