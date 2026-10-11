import json
import subprocess
import sys
from pathlib import Path

import pytest

from streamstats.analysis import Stats
from streamstats.errors import Invalid_event, Invalid_time
from streamstats.models import Event
from streamstats.parsers import choose_parser


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


def test_event_invalid_timestamp():
    raw = {
        "timestamp": "10/10/2026 12:00",
        "level": "INFO",
        "source": "auth",
        "message": "Test",
    }
    with pytest.raises(Invalid_time):
        Event.scanf(raw)


def test_event_missing_fields():
    raw1 = {"timestamp": "2026-10-10T12:00:00", "level": "INFO", "source": "auth"}
    raw2 = {"level": "INFO", "source": "auth", "message": "Test"}

    with pytest.raises(Invalid_event):
        Event.scanf(raw1)
    with pytest.raises(Invalid_event):
        Event.scanf(raw2)


def test_stats_all_in_one():
    st = Stats()

    # Запихнул инлайн прямо в вызов
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
    assert len(events) == 2
    assert parser.skip_count == 1


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
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 1
    assert "Ошибка параметров:" in res.stderr


def test_cli_unsupported_format(tmp_path: Path):
    f = tmp_path / "test.xml"
    f.write_text("<log></log>", encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "streamstats",
        "analyze",
        str(f),
        "-f",
        "xml",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 1
    assert "не csv или jsonl" in res.stderr


def test_cli_validation_error(tmp_path: Path):
    bad_file = tmp_path / "corrupt.jsonl"
    bad_file.write_text(
        '{"timestamp": "bad-date", "level": "INFO", "source": "app", "message": "fail"}\n',
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "streamstats",
        "analyze",
        str(bad_file),
        "-f",
        "jsonl",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert res.returncode == 2
    assert "Ошибка валидации:  " in res.stderr
