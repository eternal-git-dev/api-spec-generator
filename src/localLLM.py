from transformers import AutoModelForCausalLM, AutoTokenizer
import torch


class Local:
    def __init__(self, repetition_penalty, max_new_tokens, temperature, top_p, num_beams, do_sample):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.repetition_penalty = repetition_penalty
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.do_sample = do_sample

        self.checkpoint = "HuggingFaceTB/SmolLM2-1.7B-Instruct"
        self.tokenizer = AutoTokenizer.from_pretrained(self.checkpoint)

        # fp16 на GPU режет память и prefill вдвое; на CPU остаёмся на fp32 для совместимости.
        dtype = torch.float16 if self.device == "cuda" else torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            self.checkpoint,
            dtype=dtype,
            low_cpu_mem_usage=True,
        ).to(self.device)
        self.model.eval()

    @torch.inference_mode()
    def generate(self, messages):
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(
            text, return_tensors="pt", truncation=True, max_length=2048
        ).to(self.device)
        input_len = inputs["input_ids"].shape[1]

        gen_kwargs = dict(
            max_new_tokens=self.max_new_tokens,
            num_beams=1,
            do_sample=self.do_sample,
            repetition_penalty=self.repetition_penalty,
            use_cache=True,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        if self.do_sample:
            gen_kwargs["temperature"] = self.temperature
            gen_kwargs["top_p"] = self.top_p

        outputs = self.model.generate(**inputs, **gen_kwargs)

        gen_ids = outputs[0, input_len:]
        return self.tokenizer.decode(gen_ids, skip_special_tokens=True)