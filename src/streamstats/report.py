import json
from pathlib import Path


# сохраняем отчет в файл
def report(stats_d: dict, output_p: str | Path):
    path = Path(output_p)  # используется паф для удобства
    path.parent.mkdir(parents=True, exist_ok=True)  # если папка отсутствует, то создаем
    # ютф-8 обязательно для кириллицы
    with open(path, mode="w", encoding="utf-8") as f:
        # дампим в json, без ascii чтобы кирилицаа не ломала репорт
        json.dump(stats_d, f, ensure_ascii=False, indent=2)
