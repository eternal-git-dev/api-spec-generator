import argparse
import fnmatch
import yaml
import json
import re
import os
import asyncio
import time
from typing import List, Dict, Any

from parser import parse_files

from services.serviceGeneration import GenerationService


class Orchestrator:
    def __init__(self, gen_service):
        self.gen_service = gen_service


    def collect_openapi_files(self, base_directory: str, patterns: List[str]) -> List[str]:
        if not os.path.isdir(base_directory):
            raise FileNotFoundError

        result = []

        for root, dirs, files in os.walk(base_directory):
            for fname in files:
                for pattern in patterns:
                    if fnmatch.fnmatch(fname, pattern):
                        file_path = os.path.join(root, fname)
                        if os.path.isfile(file_path):
                            result.append(file_path)
        return result

    def normalize_methods(self, raw: List) -> List[Dict[str, Any]]:
        result = []

        for entry in raw:
            if not isinstance(entry, (list, tuple)) or len(entry) < 2:
                continue

            path, info = entry[0], entry[1] or {}

            for op_name in ("get", "post", "put", "patch", "delete", "options"):
                op = info.get(op_name)
                if op is None:
                    continue

                raw_params = op.get("parameters") or []

                compacted_params = []
                for param in raw_params:
                    scm = param.get("schema") or {}
                    compacted_params.append({
                        "name": param.get("name"),
                        "in": param.get("in"),
                        "required": bool(param.get("required")),
                        "type": scm.get("type") if isinstance(param, dict) else None
                    })

                doc = op.get("summary") or op.get("description") or ""

                result.append({
                    "method": f"{op_name.upper()} {path}",
                    "params": compacted_params,
                    "docstring": doc
                })
        return result


    def safe_json_loads(self, json_str: str):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            print(f"Problematic JSON: {json_str}")
            try:
                fixed_json = re.sub(r',\s*}\s*}\s*$', '}}', json_str)
                fixed_json = re.sub(r'\}\s*\}\s*$', '}}', fixed_json)
                return json.loads(fixed_json)
            except:
                return None

    def parse_methods(self, yaml_file: dict, n: int):

        paths = list(yaml_file['paths'].items())
        normalized = self.normalize_methods(paths)
        data = [normalized[i:i + n] for i in range(0, len(normalized), n)]
        return data


    def parse_llm_response(self, response: str):
        result = re.search(r"<json>(.*?)</json>", response, flags=re.DOTALL | re.IGNORECASE)
        if result is None:
            print(f"Failed to parse: {response}")
            return None
        return result.group(1)


    def add_documentation(self, files_notation_list: list, docs_list: dict) -> dict:
        result = {}

        for file_name, file_content in files_notation_list:
            result[file_name] = file_content.copy()

            if file_name not in docs_list:
                continue

            for doc_item in docs_list[file_name]:
                method_str = doc_item.get('method', '')
                if not method_str:
                    continue

                parts = method_str.split(' ', 1)
                if len(parts) != 2:
                    continue

                http_method, path = parts[0].lower(), parts[1]

                if path in file_content.get('paths', {}):
                    path_info = file_content['paths'][path]
                    if http_method in path_info:
                        if 'summary' in doc_item and doc_item['summary']:
                            path_info[http_method]['summary'] = doc_item['summary']
                        if 'description' in doc_item and doc_item['description']:
                            path_info[http_method]['description'] = doc_item['description']

        return result

    """async def process_documentation(notations: List, max_concurrency: int = 2):
        llm = await asyncio.to_thread(LLM)
        sem = asyncio.Semaphore(max_concurrency)
        result = {}
    
        async def safe_get_doc(file_name, method_chunk):
            async with sem:
                try:
                    raw = await asyncio.to_thread(llm.generate, method_chunk)
                except Exception as e:
                    print("LLM generate failed")
                    return file_name, None, e
                json_part = parse_llm_response(raw)
                parsed = safe_json_loads(json_part) if json_part else None
                return file_name, parsed, None
    
        tasks = []
    
        for file_name, methods in notations:
            chunks = parse_methods(methods, n=2)
            for chunk in chunks:
                tasks.append(asyncio.create_task(safe_get_doc(file_name, chunk)))
    
        for task in asyncio.as_completed(tasks):
            file_name, parsed, exc = await task
            if file_name not in result:
                result[file_name] = []
            if exc:
                print("Error while generating for %s: %s", file_name, exc)
                continue
            if parsed and isinstance(parsed, list):
                result[file_name].extend(parsed)
    
        return result"""

    def get_documentation(self, notations: List, max_concurrency: int = 2):
        result = {}

        for file_name, methods in notations:
            result[file_name] = []
            chunks = self.parse_methods(methods, n=max_concurrency)
            for chunk in chunks:
                raw = self.gen_service.generate(chunk)
                json_part = self.parse_llm_response(raw)
                parsed = self.safe_json_loads(json_part) if json_part else None
                if parsed and isinstance(parsed, list):
                    result[file_name].extend(parsed)

        return result



async def main(path, patterns):

    genService = GenerationService()
    orchestrator = Orchestrator(genService)
    res = orchestrator.collect_openapi_files(path, patterns)
    notation = parse_files(res)

    doc = orchestrator.get_documentation(notation)

    new_docs = orchestrator.add_documentation(notation, doc)

    for file, doc in new_docs.items():
        file = file.split(".")[0]
        print(f"Writing {file}...")
        with open(f"{file}.yaml", "w", encoding="utf-8") as f:
            yaml.dump(doc, f, allow_unicode=True, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate OpenAPI documentation from Python files.')
    parser.add_argument('--path', type=str, required=True, help='Root directory for file search')
    parser.add_argument('--patterns', type=str, nargs='+', required=True, help='File patterns (e.g. "*.py")')

    args = parser.parse_args()

    asyncio.run(main(args.path, args.patterns))