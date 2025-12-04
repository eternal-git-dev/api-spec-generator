import textwrap

from models import EndPoint
import os
import re

CLIENT_BASE = """
import requests

class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def __send(self, path: str, method: str):
        return requests.request(method, self.base_url + path)
    {methods}
""".strip()

METHOD_TEMPLATE = """
def {method_name}(self{params}):
    \"\"\"{summary}\"\"\"
    \"\"\"{description}\"\"\"
    return self.__send(f'{path}', '{method}')
"""

class ClientGenerator:
    def create_clients(self, api_files: list, output_dir: str):
        for api_file in api_files:
            file_name, endpoints = api_file
            with open(os.path.join(output_dir, file_name), 'w', encoding='utf-8') as f:
                f.write(self.create_client(endpoints))
            f.close()
            print(f'Файл {file_name} создан')

    def format_path(self, path: str) -> str:
        pattern = r'<([a-zA-Z]+):([a-zA-Z0-9_]+)>'

        def replace_match(match):
            return f'{{{match.group(2)}}}'

        return re.sub(pattern, replace_match, path)


    def create_client(self, endpoints: list[EndPoint]):
        methods = []
        for e in endpoints:
            path = self.format_path(e.path)
            for method in e.methods:
                params = ''.join([f', {param.get("name")}: {param.get("type")}' for param in e.params])
                method_name = e.function
                summary = e.summary
                description = e.description
                code = METHOD_TEMPLATE.format(
                    method_name=method_name,
                    path=path,
                    params=params,
                    method=method,
                    description=description,
                    summary=summary)
                methods.append(code)

        methods_block = textwrap.indent(''.join(methods), '    ')
        return CLIENT_BASE.format(methods=methods_block)
