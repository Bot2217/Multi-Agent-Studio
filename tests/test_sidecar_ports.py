"""The desktop entry can be asked for a separate engine port."""

import json

import pytest

from api.serve import parse_ports, write_endpoint


def test_parse_ports_reads_flags_and_env(monkeypatch):
    assert parse_ports(["--port", "8501", "--api-port", "8765"]) == ("8501", "8765")
    monkeypatch.setenv("MAS_PORT", "8502")
    monkeypatch.setenv("MAS_API_PORT", "9000")
    assert parse_ports([]) == ("8502", "9000")
    assert parse_ports(["--port", "1"]) == ("1", "9000")


def test_parse_ports_rejects_a_bad_engine_port():
    with pytest.raises(SystemExit):
        parse_ports(["--port", "8501", "--api-port", "nope"])
    with pytest.raises(SystemExit):
        parse_ports([])


def test_endpoint_file(tmp_path, monkeypatch):
    monkeypatch.setenv("MAS_DATA_DIR", str(tmp_path))
    write_endpoint("4321")
    payload = json.loads((tmp_path / "api.json").read_text(encoding="utf-8"))
    assert payload == {"port": 4321, "health": "http://127.0.0.1:4321/api/v1/health"}
