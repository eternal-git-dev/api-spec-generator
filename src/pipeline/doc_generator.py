import json
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
    def __init__(self, generation_service, max_batch: int = 2, debug: bool = False):
        self.gen = generation_service
        self.max_batch = max_batch
        self.debug = debug

    @staticmethod
    def _log(kind: str, msg: str):
        prefix = {
            "start": "→",
            "ok": "  ✓",
            "retry": "  ↻",
            "fail": "  ✗",
            "warn": "  !",
        }.get(kind, "  ")
        print(f"{prefix} {msg}")

    def _describe_chunk(self, chunk):
        names = []
        for it in chunk:
            if isinstance(it, dict):
                methods = it.get("methods") or []
                m = methods[0] if methods else "?"
                p = it.get("path") or it.get("function") or "?"
                names.append(f"{m} {p}")
        return ", ".join(names) if names else f"({len(chunk)} эндпоинтов)"

    def _parse_llm_response(self, response: str):
        m = re.search(r"<json>(.*?)</json>", response, flags=re.DOTALL | re.IGNORECASE)
        return m.group(1) if m else None

    @staticmethod
    def _detect_dup_keys(pairs):
        seen = set()
        for k, _ in pairs:
            if k in seen:
                raise ValueError(f"duplicate key: {k}")
            seen.add(k)
        return dict(pairs)

    def _safe_json_loads(self, json_str: str):
        s = json_str.strip()

        try:
            return json.loads(s, object_pairs_hook=self._detect_dup_keys)
        except ValueError:
            pass
        except json.JSONDecodeError:
            pass

        if _HAS_JSON_REPAIR:
            try:
                return json.loads(repair_json(s), object_pairs_hook=self._detect_dup_keys)
            except Exception:
                pass

        start = s.find('[')
        end = s.rfind(']')
        if start != -1 and end > start:
            try:
                return json.loads(s[start:end + 1], object_pairs_hook=self._detect_dup_keys)
            except (json.JSONDecodeError, ValueError):
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
        raw = self.gen.generate(chunk_trimmed)
        if not raw:
            return None

        json_part = self._parse_llm_response(raw)
        parsed = self._safe_json_loads(json_part) if json_part else None

        valid = []
        if isinstance(parsed, list):
            for item in parsed:
                cleaned = self._clean_doc_item(item)
                if cleaned:
                    valid.append(cleaned)

        return valid if valid else None

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
                    self._log(
                        "retry",
                        f"чанк не распарсился, пробуем по одному ({len(chunk_trimmed)})"
                    )

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

        return result
