import ast
from typing import List, Tuple
from models import EndPoint


def extract_route_info(dec: ast.Call):
    path = None
    methods = None

    if dec.args:
        path = dec.args[0]
        if isinstance(path, ast.Constant):
            path = path.value

    for kw in dec.keywords:
        if kw.arg == 'methods':
            if isinstance(kw.value, (ast.List, ast.Tuple)):
                methods = []
                for elt in kw.value.elts:
                    if isinstance(elt, ast.Constant):
                        methods.append(elt.value)
    return path, methods


def get_decorator_name(dec: ast.AST) -> str:
    if isinstance(dec, ast.Call):
        func = dec.func
    else:
        func = dec
    if isinstance(func, ast.Attribute):
        return func.attr
    elif isinstance(func, ast.Name):
        return func.id
    return ""


def get_optimized_snippet(node: ast.FunctionDef, max_lines: int = 10, max_length: int = 300) -> str:
    source = ast.unparse(node)
    lines = source.split('\n')

    if len(lines) <= max_lines and len(source) <= max_length:
        return source

    snippet_lines = lines[:max_lines]
    snippet = '\n'.join(snippet_lines)

    if len(snippet) > max_length:
        snippet = snippet[:max_length].rsplit('\n', 1)[0]

    return snippet

def parse_file(filename: str):
    with open(filename) as file:
        content = file.read()

    tree = ast.parse(content)
    endpoints = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            function_calls = extract_calls_from_function(node)

            for decorator in node.decorator_list:
                name = get_decorator_name(decorator)
                if name == "route":
                    if isinstance(decorator, ast.Call):
                        path, methods = extract_route_info(decorator)
                    else:
                        path, methods = None, None

                    doc = ast.get_docstring(node) or ""
                    summary = doc.strip().splitlines()[0] if doc else ""
                    description = doc.strip().splitlines()[1:] if doc else ""
                    params = []
                    for arg in node.args.args:
                        if arg.arg == "self":
                            continue
                        ann = None
                        if arg.annotation:
                            if isinstance(arg.annotation, ast.Name):
                                ann = arg.annotation.id
                            elif isinstance(arg.annotation, ast.Attribute):
                                ann = arg.annotation.attr
                            else:
                                ann = ast.unparse(arg.annotation)
                        params.append({"name": arg.arg, "type": ann})
                    endpoints.append(EndPoint(function=node.name, path=path or "/<unknown>",methods=methods or ["GET"],
                                              summary=summary,params=params, calls=function_calls, code_snippet=get_optimized_snippet(node), description=description))

    return endpoints


def extract_calls_from_function(func_node):
    calls = []

    for body_item in func_node.body:
        if isinstance(body_item, ast.Return) and body_item.value:
            for child in ast.walk(body_item.value):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.append(child.func.id)
                    elif isinstance(child.func, ast.Attribute):
                        parts = []
                        current = child.func
                        while isinstance(current, ast.Attribute):
                            parts.append(current.attr)
                            current = current.value
                        if isinstance(current, ast.Name):
                            parts.append(current.id)
                        calls.append('.'.join(reversed(parts)))

    return calls

def parse_files(file_dirs: List[str]) -> List[Tuple[str, list]]:
    result = []
    for file_dir in file_dirs:
        endpoints = parse_file(file_dir)
        if endpoints:
            file_name = file_dir.split("\\")[-1]
            result.append((file_name, endpoints))

    return result
