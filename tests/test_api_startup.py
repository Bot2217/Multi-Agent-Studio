"""The desktop engine must listen on localhost and must not swallow a dead thread."""

import threading

import pytest

from api.serve import ApiStartupError, _silence_signals, wait_until_listening


class _Server:
    def capture_signals(self):
        raise AssertionError("signals should not be installed")


def test_signal_handlers_are_not_installed_from_the_sidecar():
    server = _Server()
    _silence_signals(server)
    with server.capture_signals():
        pass


def test_wait_reports_a_dead_thread():
    thread = threading.Thread(target=lambda: None)
    thread.start()
    thread.join()
    assert wait_until_listening("9", thread, [], timeout=0.1) is False


def test_wait_reports_a_thread_error():
    thread = threading.Thread(target=lambda: None)
    thread.start()
    assert wait_until_listening("9", thread, [RuntimeError("boom")], timeout=0.2) is False


def test_serve_in_thread_fails_clearly_when_the_port_never_opens(monkeypatch):
    import api.serve as serve

    class Dead:
        def run(self):
            raise RuntimeError("add_signal_handler")

    monkeypatch.setattr(serve, "write_endpoint", lambda _port: None)
    monkeypatch.setattr("uvicorn.Server", lambda config: Dead())
    monkeypatch.setattr("uvicorn.Config", lambda *args, **kwargs: object())
    with pytest.raises(ApiStartupError, match="add_signal_handler"):
        serve.serve_in_thread("9", timeout=0.5)
