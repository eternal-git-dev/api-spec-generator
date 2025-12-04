import json
import re
from pipeline.utils import batch_convert_to_dicts


class DocGenerator:
    def __init__(self, generation_service, max_batch: int = 2):
        self.gen = generation_service
        self.max_batch = max_batch

    def _parse_llm_response(self, response: str):
        result = re.search(r"<json>(.*?)</json>", response, flags=re.DOTALL | re.IGNORECASE)
        return result.group(1) if result else None

    def _safe_json_loads(self, json_str: str):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            try:
                fixed_json = re.sub(r',\s*}\s*}\s*$', '}}', json_str)
                fixed_json = re.sub(r'\}\s*\}\s*$', '}}', fixed_json)
                return json.loads(fixed_json)
            except:
                return None

    def get_documentation(self, notations: list, max_concurrency: int = 2):
        result = {}

        for file_name, methods in notations:
            result[file_name] = []
            chunks = batch_convert_to_dicts(methods, max_concurrency)
            for chunk in chunks:
                print('CHUNK -------------------------------------------------')
                print(chunk)
                print('CHUNK END -------------------------------------------')
                raw = self.gen.generate(chunk)
                json_part = self._parse_llm_response(raw)
                parsed = self._safe_json_loads(json_part) if json_part else None
                if parsed and isinstance(parsed, list):
                    result[file_name].extend(parsed)

        return result