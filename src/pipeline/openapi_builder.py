import os
import yaml
from typing import List, Tuple
from models import EndPoint


class OpenApiBuilder:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def build(self, enriched_ir: List[Tuple[str, List[EndPoint]]], title: str = "API",
                           version: str = "1.0.0") -> None:
        """
        Создает отдельные YAML файлы OpenAPI 3.0 для каждого файла из enriched_ir.
        """
        # Создаем выходную директорию, если она не существует
        os.makedirs(self.output_dir, exist_ok=True)

        for file_name, methods in enriched_ir:
            openapi = {
                "openapi": "3.0.0",
                "info": {
                    "title": f"{title} - {os.path.basename(file_name)}",
                    "version": version
                },
                "paths": {}
            }

            for m in methods:
                path = m.path or f"/{os.path.basename(file_name)}/{m.function}"
                http_method = (m.methods[0] or "get").lower()

                summary = m.summary or ""
                description = m.description or ""

                parameters = []
                for p in m.params:
                    parameters.append({
                        "name": p.get("name"),
                        "in": p.get("in", "query"),
                        "required": bool(p.get("required", False)),
                        "schema": {"type": p.get("type", "string")},
                        "description": p.get("description", "")
                    })

                responses = {
                    "200": {
                        "description": "Successful Response",
                        "content": {
                            "application/json": {
                                "schema": {"response_schema", {"type": "object"}}
                            }
                        }
                    }
                }

                if path not in openapi["paths"]:
                    openapi["paths"][path] = {}

                openapi["paths"][path][http_method] = {
                    "summary": summary,
                    "description": description,
                    "parameters": parameters,
                    "responses": responses,
                }

            base_name = os.path.basename(file_name)
            name_without_ext = os.path.splitext(base_name)[0]
            output_file = os.path.join(self.output_dir, f"{name_without_ext}.yaml")
            self._safe_write(output_file, openapi)

    def _safe_write(self, output_file, openapi):
        try:
            with open(output_file, "w", encoding="utf-8") as f:
                yaml.dump(openapi, f, allow_unicode=True, encoding="utf-8",
                          default_flow_style=False, sort_keys=False)
            print(f"Created OpenAPI specification: {output_file}")
        except Exception as e:
            print(f"Error writing YAML file {output_file}: {e}")