import argparse
import fnmatch
import yaml
import re
from typing import List, Dict, Any

import asyncio

from parser import parse_files
from llm import *


def collect_openapi_files(base_directory: str, patterns: List[str]) -> List[str]:
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

def normalize_methods(raw: List) -> List[Dict[str, Any]]:
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


def safe_json_loads(json_str: str):
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
            return NoneC:\Users\eternal\PycharmProjects\LLM

def parse_methods(yaml_file: dict, n: int):

    paths = list(yaml_file['paths'].items())
    normalized = normalize_methods(paths)
    data = [normalized[i:i + n] for i in range(0, len(normalized), n)]
    return data


def parse_llm_response(response: str):
    result = re.search(r"<json>(.*?)</json>", response, flags=re.DOTALL | re.IGNORECASE)
    if result is None:
        print(f"Failed to parse {response}")
        return None
    return result.group(1)


def add_documentation(files_notation_list: list, docs_list: dict) -> dict:
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
                    # Добавляем документацию
                    if 'summary' in doc_item and doc_item['summary']:
                        path_info[http_method]['summary'] = doc_item['summary']
                    if 'description' in doc_item and doc_item['description']:
                        path_info[http_method]['description'] = doc_item['description']

    return result

async def get_documentation(method: list[dict[str, Any]], llm: LLM) -> list | None:
    llm_response = await llm.generate(method)

    json_response = parse_llm_response(llm_response)
    if not json_response:
        return None

    parsed_response = safe_json_loads(json_response)
    if parsed_response and isinstance(parsed_response, list):
        return parsed_response

    return None

async def process_documentation(notations: List):
    llm = LLM()
    result = {}

    tasks = []
    tasks_mapping = []

    for file_name, methods in notations:
        methods = parse_methods(methods, n=2)
        for method in methods:
            task = asyncio.create_task(get_documentation(method, llm))
            tasks.append(task)
            tasks_mapping.append(file_name)

    documentation_result = await asyncio.gather(*tasks, return_exceptions=True)

    for file_name, doc_result in zip(tasks_mapping, documentation_result):
        if file_name not in result:
            result[file_name] = []

        if doc_result and isinstance(doc_result, list):
            result[file_name].extend(doc_result)

    return result


async def main(path, patterns):
    res = collect_openapi_files(path, patterns)
    notation = parse_files(res)

    doc = await process_documentation(notation)

    new_docs = add_documentation(notation, doc)

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