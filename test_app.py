import os

import pytest

os.environ["ENABLE_SCHEDULER"] = "false"

import app as appmod  # noqa: E402


@pytest.fixture
def client():
    appmod.app.config["TESTING"] = True
    with appmod.app.test_client() as c:
        yield c


def _start(client):
    client.post("/start/pick", data={"team_id": "1", "difficulty": "normal"}, follow_redirects=True)
    client.post("/season/start", follow_redirects=True)


def test_landing(client):
    assert client.get("/").status_code == 200
    assert client.get("/choose-team").status_code == 200


def test_core_pages_after_start(client):
    _start(client)
    for path in ("/", "/team", "/season", "/driver-market", "/transfers",
                 "/browse?view=drivers", "/browse?view=teams"):
        assert client.get(path).status_code == 200, path


def test_full_flow(client):
    _start(client)
    assert client.post("/season/sim/rest", follow_redirects=True).status_code == 200
    assert client.get("/season/finale").status_code == 200
    assert client.post("/season/finale/run", follow_redirects=True).status_code == 200
    assert client.get("/season/year-end").status_code == 200
    assert client.post("/season/young-drivers/start", follow_redirects=True).status_code == 200
    assert client.post("/season/young-drivers/sim", data={"mode": "rest"}, follow_redirects=True).status_code == 200
    assert client.post("/season/advance", follow_redirects=True).status_code == 200


def test_404(client):
    assert client.get("/no-such-page").status_code == 404


def test_admin_hidden_by_default(client):
    # Admin disabled unless ADMIN_ENABLED is set
    assert client.get("/admin/").status_code == 404
