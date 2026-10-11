# программа для потоково чтения csv и jsonl файло

## что было реализованно в программе
- потострочное чтение файлов, используя память О(1)
- также топ 5 ошибок при равном кол-ве срабатываний сортируется лексически
- автоматическое пополнение логов в 1 единный файл
- два режима работы, с завершеннием ошибки и продолжанием работы но выводом ошибеи в файле
- используется uv, а не pip

в cli основная команда:
```bash
python -m streamstats analyze INPUT [INPUT ...] --format csv|jsonl [--output REPORT.json] [--skip-invalid]

примеры команд
 * анализ 1 или несколько файлов:
uv run python -m streamstats analyze server.jsonl app.jsonl -f jsonl -o report.json

 * запуск с пропуском ошибок:
uv run python -m streamstats analyze access.csv -f csv --skip-invalid

 * Команда хелп для помощи:
uv run python -m streamstats --help

коды возврата
 * 0 — успешное выполнение
 * 1 — ошибка параметров cli, неподдерживаемый формат или файл не найден
 * 2 — ошибка записи данных
отчет
{
  "total_events": 1500,
  "levels": {
    "INFO": 1200,
    "WARNING": 200,
    "ERROR": 80,
    "CRITICAL": 20
  },
  "sources": {
    "auth": 500,
    "database": 700,
    "api": 300
  },
  "top_5_error_sources": [
    { "source": "database", "count": 70 },
    { "source": "api", "count": 30 }
  ],
  "first_timestamp": "2026-10-10T08:00:00",
  "last_timestamp": "2026-10-10T23:59:59",
  "skipped_lines": 0
}

Тестирование и проверка
 * Запуск автоматических тестов:
uv run pytest -v

 * Проверка стиля кода и типизации(красивый код):
uv run ruff check .

 * Форматирование кода(чтобы бы красивый код):
uv run ruff format .

Архитектура и реализация проекта:
 * src/streamstats/models.py — модель записи Event, валидация и парсинг ISO 8601
 * src/streamstats/parsers.py — потоковые парсеры CSV и JSONL на используя yield
 * src/streamstats/analysis.py — Счет данных, требуемых по тз
 * src/streamstats/errors.py — исключения
 * src/streamstats/report.py — экспорт и логирование в отдельный файл
 * src/streamstats/main.py — основа - cli на argparsere
Выводы:
я познакомился с модулями csv и json, понял как можно парсить файлы построчно, чтобы не занимать всю память. Возможность чтения файла до 10 гигов.
Из интересного узнал, что чтобы про валидировать jsonl файл нужно сначала прочесть строчку, а а уже потом валидировать, наоборот нельзя, выдавало неверный ответ.
Понял принцып работы классов в пайтоне, а также что такое yield.

