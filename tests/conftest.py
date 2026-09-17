import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


@pytest.fixture(autouse=True)
def no_real_network(request, monkeypatch):
    if request.node.get_closest_marker("evaluation"):
        return
    original = socket.socket.connect

    def blocked(connection, address):
        if connection.family in (socket.AF_INET, socket.AF_INET6):
            raise AssertionError("Real network calls are forbidden in non-evaluation tests")
        return original(connection, address)

    monkeypatch.setattr(socket.socket, "connect", blocked)
