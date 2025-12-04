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

"""a = [('api.py', [EndPoint(function='group_prefixes', path='/group/prefixes', params=[], methods=['GET'], summary='Возвращает список префиксов групп.', description="Получает все группировки из хранилища и возвращает их ключи как массив в JSON-объекте с полем 'prefixes'.", calls=['jsonify', 'dict'], code_snippet="@blueprint.route('/group/prefixes', methods=['GET'])\ndef group_prefixes():\n    groupings = groups.get_groupings()\n    keys = list(groupings.keys())\n    return jsonify(dict(prefixes=keys))"), EndPoint(function='group', path='/group/<string:prefix>', params=[{'name': 'prefix', 'type': 'str'}], methods=['GET'], summary='Возвращает группы по префиксу.', description='Ищет группы по указанному префиксу в базе данных и возвращает список объектов с полями id и title в формате JSON.', calls=['jsonify'], code_snippet="@blueprint.route('/group/<string:prefix>', methods=['GET'])\ndef group(prefix: str):\n    groups = db.groups.get_by_prefix(prefix)\n    dtos = [dict(id=group.id, title=group.title) for group in groups]\n    return jsonify(dtos)"), EndPoint(function='variant_list', path='/variant/list', params=[], methods=['GET'], summary='Возвращает список идентификаторов всех вариантов.', description='Получает все варианты из хранилища данных и возвращает массив их ID в формате JSON.', calls=['jsonify'], code_snippet="@blueprint.route('/variant/list', methods=['GET'])\ndef variant_list():\n    variants = db.variants.get_all()\n    dtos = [variant.id for variant in variants]\n    return jsonify(dtos)"), EndPoint(function='task_list', path='/group/<int:gid>/variant/<int:vid>/task/list', params=[{'name': 'gid', 'type': 'int'}, {'name': 'vid', 'type': 'int'}], methods=['GET'], summary='Возвращает статусы задач для указанного варианта в группе.', description='Принимает идентификаторы группы и варианта, запрашивает статусы варианта из сервиса статусов и возвращает результат в JSON.', calls=['jsonify'], code_snippet="@blueprint.route('/group/<int:gid>/variant/<int:vid>/task/list', methods=['GET'])\ndef task_list(gid: int, vid: int):\n    variant = statuses.get_variant_statuses(gid, vid)"), EndPoint(function='task', path='/group/<int:gid>/variant/<int:vid>/task/<int:tid>', params=[{'name': 'gid', 'type': 'int'}, {'name': 'vid', 'type': 'int'}, {'name': 'tid', 'type': 'int'}], methods=['GET'], summary='Возвращает статус указанной задачи.', description='Принимает идентификаторы группы, варианта и задачи. Получает статус задачи из соответствующего хранилища.', calls=['jsonify', 'dict'], code_snippet="@blueprint.route('/group/<int:gid>/variant/<int:vid>/task/<int:tid>', methods=['GET'])\ndef task(gid: int, vid: int, tid: int):\n    status = statuses.get_task_status(gid, vid, tid)"), EndPoint(function='submit_task', path='/group/<int:gid>/variant/<int:vid>/task/<int:tid>', params=[{'name': 'gid', 'type': 'int'}, {'name': 'vid', 'type': 'int'}, {'name': 'tid', 'type': 'int'}], methods=['POST'], summary='Отправляет решение для указанной задачи.', description='Требует авторизационный токен в заголовке запроса. Принимает код решения в теле JSON-запроса и проверяет доступ перед обработкой.', calls=['jsonify', 'dict'], code_snippet="@blueprint.route('/group/<int:gid>/variant/<int:vid>/task/<int:tid>', methods=['POST'])\ndef submit_task(gid: int, vid: int, tid: int):\n    token = request.headers.get('token')\n    if config.config.api_token != token:\n        raise ValueError('Access is denied.')\n    code = request.json['code']")])]

file_name, endpoints = a[0]
print(create_client(endpoints))"""
