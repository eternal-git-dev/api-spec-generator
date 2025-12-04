POETRY := poetry
SCRIPT := .\src\main.py

PATH_ARG ?= C:\Users\eternal\PycharmProjects\LLM\data\check
PATTERNS_ARG ?= "*.py"
MODE_ARG ?= auto
OUTPUT_ARG ?= output

RUN := $(POETRY) run python $(SCRIPT)

.PHONY: help install run clean run-local run-remote

help:
	@echo "Makefile commands:"
	@echo "  install       - установить зависимости через poetry"
	@echo "  run           - запустить генерацию документации (по умолчанию auto)"
	@echo "  run-local     - запуск в local режиме"
	@echo "  run-remote    - запуск в remote режиме"
	@echo "  clean         - удалить сгенерированные файлы"
	@echo ""
	@echo "Переменные окружения для изменения аргументов:"
	@echo "  PATH_ARG      - путь к корневой папке для поиска файлов (по умолчанию .)"
	@echo "  PATTERNS_ARG  - паттерны файлов (по умолчанию \"*.py\")"
	@echo "  MODE_ARG      - режим генерации (auto/local/remote, по умолчанию auto)"
	@echo "  OUTPUT_ARG    - папка для сохранения результатов (по умолчанию output)"

install:
	$(POETRY) install

run:
	$(RUN) --path $(PATH_ARG) --patterns $(PATTERNS_ARG) --mode $(MODE_ARG) --o $(OUTPUT_ARG)

run-local:
	$(RUN) --path $(PATH_ARG) --patterns $(PATTERNS_ARG) --mode local --o $(OUTPUT_ARG)

run-remote:
	$(RUN) --path $(PATH_ARG) --patterns $(PATTERNS_ARG) --mode remote --o $(OUTPUT_ARG)

clean:
	@echo "Удаление файлов из папки $(OUTPUT_ARG)..."
	rm -rf $(OUTPUT_ARG)/*