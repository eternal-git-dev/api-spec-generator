import argparse

from pipeline.file_collector import FileCollector
from pipeline.doc_generator import DocGenerator
from pipeline.openapi_builder import OpenApiBuilder
from pipeline.client_generator import ClientGenerator
from pipeline.orchestrator import Orchestrator
from services.serviceGeneration import GenerationService



def main(path, patterns, mode, output_dir=""):

    collector = FileCollector()
    gen_service = GenerationService(mode)
    doc_gen = DocGenerator(gen_service, max_batch=2)
    openapi_builder = OpenApiBuilder(output_dir)
    client_generator = ClientGenerator()

    orchestrator = Orchestrator(collector, doc_gen, openapi_builder, client_generator)
    orchestrator.run(path, patterns, output_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Generate OpenAPI documentation from Python files.')
    parser.add_argument('--path', type=str, required=True, help='Root directory for file search')
    parser.add_argument('--patterns', type=str, nargs='+', required=True, help='File patterns (e.g. "*.py")')
    parser.add_argument('--mode', type=str, choices=['local', 'remote', 'auto'], required=True, help='Mode of generation')
    parser.add_argument('--o', type=str, required=True, help='Root directory for output files save')

    args = parser.parse_args()
    main(args.path, args.patterns, args.mode, args.o)