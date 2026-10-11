import csv
import json
import logging

from .errors import Stream_stats_error, Unsupported_format
from .models import Event

logger = logging.getLogger("streamstats")


class Parser:
    def __init__(self, file_path: str, skip_errors=False):
        self.file_path = str(file_path)
        self.skip_errors = skip_errors
        self.skip_count = 0

    def parse(self):
        raise NotImplementedError("Неверно написан парсер")


def choose_parser(file_path: str, f_format: str, skip_errors: bool = False):
    form = f_format.strip()

    if form == "jsonl":
        return JSONL_parser(file_path, skip_errors=skip_errors)
    if form == "csv":
        return CSV_parser(file_path, skip_errors=skip_errors)
    else:
        raise Unsupported_format(f"формат файла {f_format} не csv или jsonl")


class CSV_parser(Parser):
    def parse(self):
        with open(self.file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            line_n = 1
            for row in reader:
                line_n += 1
                try:
                    yield Event.scanf(row, file_path=self.file_path, line_number=line_n)
                except Stream_stats_error as error:
                    if self.skip_errors:
                        self.skip_count += 1
                        logger.warning(error)
                    else:
                        raise error


class JSONL_parser(Parser):
    def parse_l(self, line: str, line_n: int):
        try:
            data = json.loads(line)
        except json.JSONDecodeError as err:
            raise Stream_stats_error(
                f"JSON имеет неверную структуру или ошибку: {err.msg}",
                file_path=self.file_path,
                line_number=line_n,
            )

        if not isinstance(data, dict):
            raise Stream_stats_error(
                "Строка должна быть словарём",
                file_path=self.file_path,
                line_number=line_n,
            )

        return Event.scanf(data, file_path=self.file_path, line_number=line_n)

    def parse(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue

                try:
                    yield self.parse_l(clean_line, line_num)
                except Stream_stats_error as err:
                    if self.skip_errors:
                        self.skip_count += 1
                        logger.warning(err)
                    else:
                        raise
