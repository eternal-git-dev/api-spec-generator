from gooey import Gooey, GooeyParser

from pipeline.file_collector import FileCollector
from pipeline.doc_generator import DocGenerator
from pipeline.openapi_builder import OpenApiBuilder
from pipeline.client_generator import ClientGenerator
from pipeline.orchestrator import Orchestrator
from services.serviceGeneration import GenerationService


@Gooey(
    program_name="Создание API-клиентов и OpenAPI документации",
    program_description="Создает API-клиенты и OpenAPI спецификацию на основе анализа файлов исходного кода"
)
def main():
    parser = GooeyParser(description='Generate OpenAPI documentation and API-clients from source files.')

    parser.add_argument(
        '--path',
        metavar='Путь к проекту',
        required=True,
        help='Корневая директория, в которой будет выполняться поиск файлов',
        widget='DirChooser'
    )

    parser.add_argument(
        '--patterns',
        metavar='Шаблоны файлов',
        required=True,
        help='Шаблоны имён файлов через пробел (например: *.py)',
    )

    parser.add_argument(
        '--mode',
        metavar='Режим',
        required=True,
        choices=['local', 'remote', 'auto'],
        help='Режим генерации (local/remote/auto)',
        widget='Dropdown'
    )

    parser.add_argument(
        '--o',
        metavar='Папка вывода',
        required=True,
        help='Корневая директория для сохранения результатов',
        widget='DirChooser'
    )

    args = parser.parse_args()

    collector = FileCollector()
    gen_service = GenerationService(args.mode)
    doc_gen = DocGenerator(gen_service, max_batch=2)
    openapi_builder = OpenApiBuilder(args.o)
    client_generator = ClientGenerator()

    orchestrator = Orchestrator(collector, doc_gen, openapi_builder, client_generator)
    orchestrator.run(args.path, args.patterns, args.o)


if __name__ == "__main__":
    main()