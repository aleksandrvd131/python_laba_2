import argparse
import logging
import sys
from pathlib import Path

from .analysis import Stats
from .errors import Cli_config, Stream_stats_error, Unsupported_format
from .parsers import choose_parser
from .report import report


def main():
    logging.basicConfig(level=logging.WARNING, format="[%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="анализ логов")
    subparsers = parser.add_subparsers(dest="command", required=True)
    analyze_parser = subparsers.add_parser("analyze", help="Анализ логов")
    analyze_parser.add_argument("files", nargs="+", help="Входные файлы")
    analyze_parser.add_argument(
        "-f", "--format", required=True, help="Формат: csv или jsonl"
    )
    analyze_parser.add_argument(
        "-o", "--output", default="report.json", help="Файл отчета"
    )
    analyze_parser.add_argument(
        "--skip-invalid",
        action="store_true",
        help="Пропуск ошибок и запись в отдельный файл",
    )
    args = parser.parse_args()
    stats = Stats()

    try:
        for str_file in args.files:
            path = Path(str_file)
            if not path.is_file():
                raise Cli_config(f"Ошибка: файл не найден:{path}")
            parser_o = choose_parser(str(path), args.format, args.skip_invalid)
            for event in parser_o.parse():
                stats.add_event(event)
            stats.add_skipped(parser_o.skip_count)
        report(stats.export_stats(), args.output)
        sys.exit(0)

    except (Cli_config, Unsupported_format) as error:
        print(f"Ошибка параметров: {error}", file=sys.stderr)
        sys.exit(1)
    except Stream_stats_error as errors:
        print(f"Ошибка валидации:  {errors}", file=sys.stderr)
        sys.exit(2)
    except Exception as error:  # noqa: BLE001
        print(f"Непредвиденная ошибка: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
