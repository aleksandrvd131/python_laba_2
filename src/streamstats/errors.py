# exceptions ошибки
class StreamStatsError(Exception):
    def __init__(
        self,
        message: str,
        *,
        file_path: str | None = None,
        line_number: int | None = None,
    ):
        super().__init__(message)  # перевод текст в стандартный Exception
        self.message = message
        self.file_path = file_path
        self.line_number = line_number

    # вывод в консоль с информаией
    def __str__(self) -> str:
        if self.file_path and self.line_number is not None:
            return f"Файл '{self.file_path}', строка {self.line_number}: {self.message}"
        if self.file_path:
            return f"Файл '{self.file_path}': {self.message}"
        return self.message


# если формат не csv и не jsonl
class UnsupportedFormatError(StreamStatsError):
    "Неподдерживаемый формат файла"


# неверные аргументы в термминале
class CLIConfigError(StreamStatsError):
    "Ошибка параметров конфигурации CLI"


# что-то незапарсилось
class InvalidEventError(StreamStatsError):
    "Некорректная событие"


# если дата не парсится по исо
class InvalidTimestampError(StreamStatsError):
    "Некорректная временная метка ISO 8601"


# поломалось все изза руфа, пришлось делать костыль, чтобы не переписывать весь говнокод)
Stream_stats_error = StreamStatsError
Unsupported_format = UnsupportedFormatError
Cli_config = CLIConfigError
Invalid_event = InvalidEventError
Invalid_time = InvalidTimestampError
