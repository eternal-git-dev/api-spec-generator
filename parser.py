import ast
from typing import List, Dict, Any


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

def parse_file(filename: str):
    with open(filename) as f:
        f = f.read()

    tree = ast.parse(f)

    endpoints = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                name = get_decorator_name(decorator)
                if name == "route":

                    if isinstance(decorator, ast.Call):
                        path, methods = extract_route_info(decorator)
                    else:
                        path, methods = None, None
                    doc = ast.get_docstring(node) or ""
                    summary = doc.strip().splitlines()[0] if doc else ""
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
                        #print("ann", arg.arg, ann)
                        params.append({"name": arg.arg, "type": ann})
                        endpoints.append({
                            "function": node.name,
                            "path": path or "/<unknown>",
                            "methods": methods or ["GET"],
                            "summary": summary,
                            "params": params,
                        })
    return endpoints

def parse_files(file_dirs: List[str]) -> list[tuple[str, dict[str, Any]]]:
    result = []
    for file_dir in file_dirs:
        endpoints = parse_file(file_dir)
        if endpoints:
            openapi = build_openapi(endpoints)
            file_name = file_dir.split("\\")[-1]
            result.append((file_name, openapi))

    return result

def build_openapi(endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
    openapi = {
        "openapi": "3.1.0",
        "info": {"title": "Auto-generated API", "version": "0.0.1"},
        "paths": {}
    }
    for ep in endpoints:
        path = ep["path"]
        if path not in openapi["paths"]:
            openapi["paths"][path] = {}
        for method in ep["methods"]:
            m = method.lower()
            openapi["paths"][path][m] = {
                "summary": ep["summary"],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"type": "object"}
                            }
                        }
                    }
                }
            }
            if ep["params"]:
                params_list = []
                for p in ep["params"]:
                    if "id" in p["name"].lower():
                        params_list.append({
                            "name": p["name"],
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}
                        })
                    else:
                        params_list.append({
                            "name": p["name"],
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"}
                        })
                openapi["paths"][path][m]["parameters"] = params_list
    return openapi
