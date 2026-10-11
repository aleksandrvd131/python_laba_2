from collections import Counter

from .models import Event


# класс для сбора и подсчета всей статистики
class Stats:
    def __init__(self):
        self.c_events = 0
        self.levels = Counter()
        self.soursec = Counter()
        self.error_s = Counter()  # только ошибки по источникам
        self.skip_l = 0
        # границы по времени
        self.min_time = None
        self.max_time = None

    def add_event(self, event: Event):
        self.c_events += 1

        # подсчет левелов и сурсов
        self.levels[event.level] += 1
        self.soursec[event.source] += 1

        # счет ошибок
        if event.level in ("ERROR", "CRITICAL"):
            self.error_s[event.source] += 1

        # считаем мин и макс время
        if self.min_time is None or event.timestamp < self.min_time:
            self.min_time = event.timestamp
        if self.max_time is None or event.timestamp > self.max_time:
            self.max_time = event.timestamp

    # прибавляем число пропущенных строк
    def add_skipped(self, count: int):
        self.skip_l += count

    # выгрузка итогового словаря
    def export_stats(self, top_n: int = 5):
        # сортировка: сначала по убыванию количества, потом по алфавиту источника
        sorted_errors = sorted(
            self.error_s.items(), key=lambda item: (-item[1], item[0])
        )[:top_n]
        top_errors = [
            {"source": source, "count": count} for source, count in sorted_errors
        ]
        # формируем итоговый dict под json
        return {
            "total_events": self.c_events,
            "levels": dict(self.levels),
            "sources": dict(self.soursec),
            "top_5_error_sources": top_errors,
            # переводим дату обратно в исо формат если есть
            "first_timestamp": self.min_time.isoformat() if self.min_time else None,
            "last_timestamp": self.max_time.isoformat() if self.max_time else None,
            "skipped_lines": self.skip_l,
        }
