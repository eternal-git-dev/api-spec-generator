from dataclasses import asdict


def batch_convert_to_dicts(methods: list, chunk_size):
    chunks = [methods[i:i + chunk_size] for i in range(0, len(methods), chunk_size)]
    return [[asdict(item) for item in chunk] for chunk in chunks]

def to_openapi_type(python_type: str) -> str:
    type_map = {
        "int": "integer",
        "float": "number",
        "str": "string",
        "bool": "boolean",
        "list": "array",
        "dict": "object",
        "None": "null",
    }
    return type_map.get(python_type.lower(), "string")