import hashlib
import json
import pathlib
import re

from pipeline.utils import batch_convert_to_dicts

try:
    from json_repair import repair_json
    _HAS_JSON_REPAIR = True
except ImportError:
    _HAS_JSON_REPAIR = False


_ALLOWED_FIELDS = ("method", "summary", "description")
_INPUT_FIELDS_TO_KEEP = ("function", "path", "methods", "code_snippet")


def _trim_input_chunk(chunk):
    trimmed = []
    for item in chunk:
        if isinstance(item, dict):
            trimmed.append({k: item[k] for k in _INPUT_FIELDS_TO_KEEP if k in item})
        else:
            trimmed.append(item)
    return trimmed


class DocGenerator:
    def __init__(self, generation_service, max_batch: int = 2,
                 cache_path: str = "doc_cache.json", debug: bool = False):
        self.gen = generation_service
        self.max_batch = max_batch
        self.cache_path = pathlib.Path(cache_path)
        self.debug = debug
        self._cache = self._load_cache()


    @staticmethod
    def _log(kind: str, msg: str):
        prefix = {
            "start":  "→",
            "ok":     "  ✓",
            "cache":  "  ⚡",
            "retry":  "  ↻",
            "fail":   "  ✗",
            "warn":   "  !",
        }.get(kind, "  ")
        print(f"{prefix} {msg}")

    def _describe_chunk(self, chunk):
        """Короткое имя чанка для логов: 'GET /foo, POST /bar' или '(1 эндпоинт)'."""
        names = []
        for it in chunk:
            if isinstance(it, dict):
                methods = it.get("methods") or []
                m = methods[0] if methods else "?"
                p = it.get("path") or it.get("function") or "?"
                names.append(f"{m} {p}")
        return ", ".join(names) if names else f"({len(chunk)} эндпоинтов)"


    def _load_cache(self):
        if self.cache_path.exists():
            try:
                return json.loads(self.cache_path.read_text(encoding='utf-8'))
            except Exception:
                return {}
        return {}

    def _save_cache(self):
        self.cache_path.write_text(
            json.dumps(self._cache, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )

    def _cache_key(self, chunk):
        payload = json.dumps(chunk, sort_keys=True, default=str, ensure_ascii=False)
        return hashlib.sha1(payload.encode('utf-8')).hexdigest()


    def _parse_llm_response(self, response: str):
        m = re.search(r"<json>(.*?)</json>", response, flags=re.DOTALL | re.IGNORECASE)
        return m.group(1) if m else None

    def _safe_json_loads(self, json_str: str):
        s = json_str.strip()
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            pass
        if _HAS_JSON_REPAIR:
            try:
                return json.loads(repair_json(s))
            except Exception:
                pass
        start = s.find('[')
        end = s.rfind(']')
        if start != -1 and end > start:
            try:
                return json.loads(s[start:end + 1])
            except json.JSONDecodeError:
                pass
        return None


    def _clean_doc_item(self, item):
        if not isinstance(item, dict):
            return None
        cleaned = {k: item[k] for k in _ALLOWED_FIELDS if k in item}
        if "method" not in cleaned:
            return None
        summary = (cleaned.get("summary") or "").strip()
        description = (cleaned.get("description") or "").strip()
        if not summary or not description:
            return None
        cleaned["summary"] = summary
        cleaned["description"] = description
        return cleaned


    def _generate_and_parse(self, chunk_trimmed):
        key = self._cache_key(chunk_trimmed)
        raw = self._cache.get(key)
        cache_was_hit = raw is not None

        if raw is None:
            raw = self.gen.generate(chunk_trimmed)
        elif self.debug:
            self._log("cache", "из кэша")

        if not raw:
            return None

        if self.debug:
            print(f"    raw={raw!r}")

        json_part = self._parse_llm_response(raw)
        parsed = self._safe_json_loads(json_part) if json_part else None

        valid = []
        if isinstance(parsed, list):
            for item in parsed:
                cleaned = self._clean_doc_item(item)
                if cleaned:
                    valid.append(cleaned)

        if valid:
            if not cache_was_hit:
                self._cache[key] = raw
                self._save_cache()
            return valid

        if cache_was_hit:
            self._cache.pop(key, None)
            self._save_cache()
        return None

    def get_documentation(self, notations: list, max_concurrency: int = 2):
        result = {}

        for file_name, methods in notations:
            print(f"\n📄 {file_name}")
            result[file_name] = []
            chunks = batch_convert_to_dicts(methods, max_concurrency)

            for chunk in chunks:
                chunk_trimmed = _trim_input_chunk(chunk)
                label = self._describe_chunk(chunk_trimmed)
                self._log("start", label)

                parsed = self._generate_and_parse(chunk_trimmed)

                if parsed:
                    result[file_name].extend(parsed)
                    self._log("ok", f"{len(parsed)} эндпоинт(ов) задокументировано")
                    continue

                if len(chunk_trimmed) > 1:
                    self._log("retry", f"чанк не распарсился, пробуем по одному ({len(chunk_trimmed)})")
                    any_ok = False
                    for single in chunk_trimmed:
                        single_label = self._describe_chunk([single])
                        single_parsed = self._generate_and_parse([single])
                        if single_parsed:
                            result[file_name].extend(single_parsed)
                            self._log("ok", f"{single_label}")
                            any_ok = True
                        else:
                            self._log("fail", f"{single_label} — пустой/невалидный ответ модели")
                    if not any_ok:
                        self._log("warn", "ни один метод в чанке не удалось обработать")
                else:
                    self._log("fail", f"{label} — пустой/невалидный ответ модели")

        print()
        return result