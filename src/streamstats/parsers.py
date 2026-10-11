import csv
import json
import logging

from .errors import Stream_stats_error, Unsupported_format
from .models import Event

# логгер для вывода предупреждений при пропуске ошибок
logger = logging.getLogger("streamstats")


# базовый класс, от него наследуем парсеры под разные форматы
class Parser:
    def __init__(self, file_path: str, skip_errors=False):
        self.file_path = str(file_path)
        self.skip_errors = skip_errors
        self.skip_count = 0  # счетчик сколько строк пропустили

    # заглушка, метод переопределяется в наследниках, если ничего не подходит - ошибка
    def parse(self):
        raise NotImplementedError("Неверно написан парсер")


# выбор нужного парсера по строке формата
def choose_parser(file_path: str, f_format: str, skip_errors: bool = False):
    form = f_format.strip()  # убираем лишние пробелы по краям

    if form == "jsonl":
        return JSONL_parser(file_path, skip_errors=skip_errors)
    if form == "csv":
        return CSV_parser(file_path, skip_errors=skip_errors)
    else:
        # если передали что-то левое, бросаем исключение
        raise Unsupported_format(f"формат файла {f_format} не csv или jsonl")


# парсер для csv файлов
class CSV_parser(Parser):
    def parse(self):
        with open(self.file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            line_n = 1  # 1 потому что первой строкой идет заголовок
            for row in reader:
                line_n += 1
                try:
                    # возвращает объект события через генератор
                    yield Event.scanf(row, file_path=self.file_path, line_number=line_n)
                except Stream_stats_error as error:
                    # если включен флаг пропускаем и логируем, иначе сразу падает программа
                    if self.skip_errors:
                        self.skip_count += 1
                        logger.warning(error)
                    else:
                        raise


# парсер для jsonl построчно
class JSONL_parser(Parser):
    # разбор отдельной строки
    def parse_l(self, line: str, line_n: int):
        try:
            data = json.loads(line)
        except json.JSONDecodeError as err:
            raise Stream_stats_error(
                f"JSON имеет неверную структуру или ошибку: {err.msg}",
                file_path=self.file_path,
                line_number=line_n,
            )

        # проверяем что внутри именно словарь, а не число или массив
        if not isinstance(data, dict):
            raise Stream_stats_error(
                "Строка должна быть словарём",
                file_path=self.file_path,
                line_number=line_n,
            )

        return Event.scanf(data, file_path=self.file_path, line_number=line_n)

    def parse(self):
        # читаем построчно чтобы не загружать огромный файл целиком в память
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue  # пустые строки просто пропускаем

                try:
                    yield self.parse_l(clean_line, line_num)
                except Stream_stats_error as err:
                    if self.skip_errors:
                        self.skip_count += 1
                        logger.warning(err)
                    else:
                        raise
