import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

from streamstats.analysis import Stats
from streamstats.errors import Invalid_event, Invalid_time
from streamstats.models import Event
from streamstats.parsers import choose_parser


# базовый эвент, все поля на месте
def test_event_valid():
    raw = {
        "timestamp": "2026-10-10T12:00:00",
        "level": "INFO",
        "source": "auth",
        "message": "User logged in",
    }
    ev = Event.scanf(raw)
    assert ev.level == "INFO"
    assert ev.source == "auth"
    assert ev.message == "User logged in"


# левый уровень лога, фатал нет в списке
def test_event_invalid_level():
    raw = {
        "timestamp": "2026-10-10T12:00:00",
        "level": "FATAL",
        "source": "auth",
        "message": "Crash",
    }
    with pytest.raises(Invalid_event) as exc_info:
        Event.scanf(raw)
    assert "FATAL" in str(exc_info.value)


# дата не по исошке
def test_event_invalid_timestamp():
    raw = {
        "timestamp": "10/10/2026 12:00",
        "level": "INFO",
        "source": "auth",
        "message": "Test",
    }
    with pytest.raises(Invalid_time):
        Event.scanf(raw)


# когда забыли поля передать
def test_event_missing_fields():
    raw1 = {
        "timestamp": "2026-10-10T12:00:00",
        "level": "INFO",
        "source": "auth",
    }  # без месседжа
    raw2 = {"level": "INFO", "source": "auth", "message": "Test"}  # без времени

    with pytest.raises(Invalid_event):
        Event.scanf(raw1)
    with pytest.raises(Invalid_event):
        Event.scanf(raw2)


# стата в кучу: добавляем события и чекаем экспорт
def test_stats_all_in_one():
    st = Stats()

    # закинул инлайн прямо в метод
    st.add_event(
        Event.scanf(
            {
                "timestamp": "2026-10-10T10:00:00",
                "level": "INFO",
                "source": "web",
                "message": "Request ok",
            }
        )
    )
    st.add_event(
        Event.scanf(
            {
                "timestamp": "2026-10-10T12:00:00",
                "level": "ERROR",
                "source": "db",
                "message": "Timeout",
            }
        )
    )
    st.add_skipped(3)

    data = st.export_stats()
    assert data["total_events"] == 2
    assert data["skipped_lines"] == 3
    assert data["levels"]["INFO"] == 1
    assert data["levels"]["ERROR"] == 1
    assert data["first_timestamp"] == "2026-10-10T10:00:00"
    assert data["last_timestamp"] == "2026-10-10T12:00:00"
    assert data["top_5_error_sources"][0] == {"source": "db", "count": 1}


# парсер ксв со скипом битых строк
def test_csv_parser_skip_errors(tmp_path: Path):
    p = tmp_path / "test.csv"
    p.write_text(
        "timestamp,level,source,message\n"
        "2026-10-10T10:00:00,INFO,api,OK\n"
        "2026-10-10T11:00:00,WRONG,api,Bad\n"
        "2026-10-10T12:00:00,ERROR,api,Fail\n",
        encoding="utf-8",
    )
    parser = choose_parser(str(p), f_format="csv", skip_errors=True)
    events = list(parser.parse())
    assert len(events) == 2  # среднюю выкинуло
    assert parser.skip_count == 1


# тесты консоли кли


# обычный успешный прогон
def test_cli_success(tmp_path: Path):
    log_file = tmp_path / "app.jsonl"
    report_file = tmp_path / "output.json"
    log_file.write_text(
        '{"timestamp": "2026-10-10T10:00:00", "level": "INFO", "source": "app", "message": "OK"}\n',
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "streamstats",
        "analyze",
        str(log_file),
        "-f",
        "jsonl",
        "-o",
        str(report_file),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 0
    assert report_file.is_file()

    saved = json.loads(report_file.read_text(encoding="utf-8"))
    assert saved["total_events"] == 1


# файла нет, должен вернуть 1
def test_cli_file_not_found():
    cmd = [
        sys.executable,
        "-m",
        "streamstats",
        "analyze",
        "missing_file_404.jsonl",
        "-f",
        "jsonl",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 1
    assert "Ошибка параметров:" in res.stderr


# неподдерживаемый формат, тоже код 1
def test_cli_unsupported_format(tmp_path: Path):
    f = tmp_path / "test.xml"
    f.write_text("<log></log>", encoding="utf-8")

    cmd = [sys.executable, "-m", "streamstats", "analyze", str(f), "-f", "xml"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 1
    assert "не csv или jsonl" in res.stderr


# битая дата в клишке -> код 2
def test_cli_validation_error(tmp_path: Path):
    bad_file = tmp_path / "corrupt.jsonl"
    bad_file.write_text(
        '{"timestamp": "bad-date", "level": "INFO", "source": "app", "message": "fail"}\n',
        encoding="utf-8",
    )

    cmd = [sys.executable, "-m", "streamstats", "analyze", str(bad_file), "-f", "jsonl"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 2
    assert "Ошибка валидации:" in res.stderr


# обязательные тесты из тз


# пустой файл -> пустой отчет с нулями
def test_empty_file_zero_report(tmp_path: Path):
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    out = tmp_path / "report_empty.json"

    cmd = [
        sys.executable,
        "-m",
        "streamstats",
        "analyze",
        str(empty),
        "-f",
        "jsonl",
        "-o",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 0
    assert out.is_file()

    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["total_events"] == 0
    assert saved["first_timestamp"] is None
    assert saved["last_timestamp"] is None
    assert saved["skipped_lines"] == 0


# рез-т из ксв и джсонл должен совпадать точь-в-точь
def test_csv_and_jsonl_same_stats(tmp_path: Path):
    f_csv = tmp_path / "data.csv"
    f_jsonl = tmp_path / "data.jsonl"
    out_csv = tmp_path / "out_csv.json"
    out_jsonl = tmp_path / "out_jsonl.json"

    f_csv.write_text(
        "timestamp,level,source,message\n"
        "2026-10-10T10:00:00,INFO,auth,login\n"
        "2026-10-10T11:00:00,ERROR,db,timeout\n",
        encoding="utf-8",
    )
    f_jsonl.write_text(
        '{"timestamp": "2026-10-10T10:00:00", "level": "INFO", "source": "auth", "message": "login"}\n'
        '{"timestamp": "2026-10-10T11:00:00", "level": "ERROR", "source": "db", "message": "timeout"}\n',
        encoding="utf-8",
    )

    cmd1 = [
        sys.executable,
        "-m",
        "streamstats",
        "analyze",
        str(f_csv),
        "-f",
        "csv",
        "-o",
        str(out_csv),
    ]
    cmd2 = [
        sys.executable,
        "-m",
        "streamstats",
        "analyze",
        str(f_jsonl),
        "-f",
        "jsonl",
        "-o",
        str(out_jsonl),
    ]

    subprocess.run(cmd1, capture_output=True, text=True, check=False)
    subprocess.run(cmd2, capture_output=True, text=True, check=False)

    data1 = json.loads(out_csv.read_text(encoding="utf-8"))
    data2 = json.loads(out_jsonl.read_text(encoding="utf-8"))
    assert data1 == data2


# если передали сразу 2 файла в аргументы
def test_multiple_files_aggregation(tmp_path: Path):
    f1 = tmp_path / "f1.jsonl"
    f2 = tmp_path / "f2.jsonl"
    out = tmp_path / "out_multi.json"

    f1.write_text(
        '{"timestamp": "2026-10-10T10:00:00", "level": "INFO", "source": "s1", "message": "m1"}\n',
        encoding="utf-8",
    )
    f2.write_text(
        '{"timestamp": "2026-10-10T11:00:00", "level": "WARNING", "source": "s2", "message": "m2"}\n',
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "streamstats",
        "analyze",
        str(f1),
        str(f2),
        "-f",
        "jsonl",
        "-o",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 0

    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["total_events"] == 2
    assert saved["levels"]["INFO"] == 1
    assert saved["levels"]["WARNING"] == 1
    assert saved["sources"]["s1"] == 1
    assert saved["sources"]["s2"] == 1


# чек чтоб кириллица не сломалась в юникод типа \u0430
def test_cyrillic_preservation(tmp_path: Path):
    log_file = tmp_path / "cyr.jsonl"
    out = tmp_path / "out_cyr.json"

    log_file.write_text(
        '{"timestamp": "2026-10-10T12:00:00", "level": "INFO", "source": "авторизация", "message": "Успешный вход"}\n',
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "streamstats",
        "analyze",
        str(log_file),
        "-f",
        "jsonl",
        "-o",
        str(out),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=False)

    text = out.read_text(encoding="utf-8")
    assert "авторизация" in text  # смотрим что в сыром файле русские буквы
    saved = json.loads(text)
    assert "авторизация" in saved["sources"]


# ломаем 7-ю строчку, чекаем что в выводе цифра 7
def test_invalid_json_line_7_reports_line_7(tmp_path: Path):
    f = tmp_path / "line7.jsonl"
    lines = [
        '{"timestamp": "2026-10-10T10:00:00", "level": "INFO", "source": "app", "message": "ok"}'
        for _ in range(6)
    ]
    lines.append("{невалидный json строка 7")  # 7-я строка
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cmd = [sys.executable, "-m", "streamstats", "analyze", str(f), "-f", "jsonl"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)

    assert res.returncode == 2
    assert "7" in res.stderr


# тут в 3 строке кривая дата
def test_invalid_date_reports_field_and_line(tmp_path: Path):
    f = tmp_path / "bad_date.csv"
    f.write_text(
        "timestamp,level,source,message\n"
        "2026-10-10T10:00:00,INFO,app,ok\n"
        "НЕ_ДАТА,INFO,app,crash\n",  # вот она 3я
        encoding="utf-8",
    )

    cmd = [sys.executable, "-m", "streamstats", "analyze", str(f), "-f", "csv"]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)

    assert res.returncode == 2
    err = res.stderr.lower()
    assert "3" in err
    assert "дат" in err or "timestamp" in err  # препод мог написать дата или timestamp


# без флага должно падать на первой же ошибке
def test_without_skip_invalid_stops(tmp_path: Path):
    f = tmp_path / "stop.jsonl"
    out = tmp_path / "out_stop.json"
    f.write_text(
        '{"timestamp": "2026-10-10T10:00:00", "level": "INFO", "source": "app", "message": "ok"}\n'
        '{"битая": "строка"}\n'
        '{"timestamp": "2026-10-10T12:00:00", "level": "INFO", "source": "app", "message": "ok"}\n',
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "streamstats",
        "analyze",
        str(f),
        "-f",
        "jsonl",
        "-o",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)

    assert res.returncode == 2
    assert not out.is_file()  # файл не должен создаться если упало


# а с флагом скипает битую и доходит до конца
def test_with_skip_invalid_keeps_going(tmp_path: Path):
    f = tmp_path / "skip.jsonl"
    out = tmp_path / "out_skip.json"
    f.write_text(
        '{"timestamp": "2026-10-10T10:00:00", "level": "INFO", "source": "app", "message": "ok1"}\n'
        '{"битая": "строка"}\n'
        '{"timestamp": "2026-10-10T12:00:00", "level": "INFO", "source": "app", "message": "ok2"}\n',
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "streamstats",
        "analyze",
        str(f),
        "-f",
        "jsonl",
        "-o",
        str(out),
        "--skip-invalid",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)

    assert res.returncode == 0
    saved = json.loads(out.read_text(encoding="utf-8"))
    assert saved["total_events"] == 2
    assert saved["skipped_lines"] == 1


# сортировка по алфавиту если каунты одинаковые
def test_top_5_deterministic_sort():
    st = Stats()
    for src in ("zeta", "alpha", "gamma"):
        st.add_event(
            Event.scanf(
                {
                    "timestamp": "2026-10-10T12:00:00",
                    "level": "ERROR",
                    "source": src,
                    "message": "err",
                }
            )
        )

    data = st.export_stats(top_n=3)
    sources = [item["source"] for item in data["top_5_error_sources"]]
    assert sources == ["alpha", "gamma", "zeta"]  # alpha, gamma, zeta


# исходные файлы не должны меняться
def test_source_files_not_modified(tmp_path: Path):
    f = tmp_path / "readonly.jsonl"
    original_text = '{"timestamp": "2026-10-10T10:00:00", "level": "INFO", "source": "app", "message": "ok"}\n'
    f.write_text(original_text, encoding="utf-8")

    cmd = [sys.executable, "-m", "streamstats", "analyze", str(f), "-f", "jsonl"]
    subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert f.read_text(encoding="utf-8") == original_text


# генератор должен читать построчно а не весь файл сразу в память
def test_large_input_not_read_entirely(tmp_path: Path):
    f = tmp_path / "stream.jsonl"
    f.write_text(
        '{"timestamp": "2026-10-10T10:00:00", "level": "INFO", "source": "app", "message": "ok"}\n'
        '{"сломанный": "json", невалидная строка\n',
        encoding="utf-8",
    )

    parser = choose_parser(str(f), f_format="jsonl", skip_errors=False)
    gen = parser.parse()

    # чек что генератор, берем только первый эвент без падения на второй строке
    assert inspect.isgenerator(gen)
    first_event = next(gen)
    assert first_event.source == "app"
