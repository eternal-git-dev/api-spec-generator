from typing import List, Dict, Tuple
from models import EndPoint
from pathlib import Path
from parser import parse_files

class Orchestrator:
    def __init__(self, collector , doc_gen, openapi_builder, client_generator):
        self.collector = collector
        self.doc_gen = doc_gen
        self.openapi_builder = openapi_builder
        self.client_generator = client_generator

    def run(self, base_dir: str, patterns: List[str], output_dir: str):
        files = self.collector.collect(Path(base_dir), patterns)
        notation = parse_files([str(p) for p in files])
        documentation = self.doc_gen.get_documentation(notation)
        enriched = self._merge_docs(notation, documentation)
        #self.openapi_builder.build(enriched)
        self.client_generator.create_clients(enriched, Path(output_dir))

    def _merge_docs(self, enriched_ir: List[Tuple[str, List[EndPoint]]], documentation: Dict[str, List[dict]]):
        doc_lookup = {}
        for file_name, doc_methods in documentation.items():
            for doc_method in doc_methods:
                req, method_path = doc_method.get("method", "").split()
                key = (file_name, method_path, req)
                doc_lookup[key] = doc_method
        for file_name, ir_methods in enriched_ir:
            for ir_method in ir_methods:
                method_path = ir_method.path or f"/{file_name}/{ir_method.function}"
                reqs = ir_method.methods or []

                for req in reqs:
                    key = (file_name, method_path, req)
                    if key in doc_lookup:
                        doc_method = doc_lookup[key]
                        ir_method.summary = doc_method.get("summary", "")
                        ir_method.description = doc_method.get("description", "")
        return enriched_ir
