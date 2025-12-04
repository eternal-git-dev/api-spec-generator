from dataclasses import dataclass


@dataclass
class EndPoint:
    function: str
    path: str
    params: list[dict]
    methods: list[str]
    summary: str
    description: str
    calls: list[str]
    code_snippet: str
