import pytest


@pytest.fixture
def board(client, auth):
    h = auth()
    b = client.post("/api/boards", json={"name": "Sprint"}, headers=h).json()
    return h, b["id"]


def titles(client, h, board_id, status):
    tasks = client.get(f"/api/boards/{board_id}/tasks", headers=h).json()
    return [t["title"] for t in tasks if t["status"] == status]


def test_create_and_positions(client, board):
    h, bid = board
    for title in ["a", "b", "c"]:
        r = client.post(f"/api/boards/{bid}/tasks", json={"title": title}, headers=h)
        assert r.status_code == 201
    tasks = client.get(f"/api/boards/{bid}/tasks", headers=h).json()
    assert [(t["title"], t["position"]) for t in tasks] == [("a", 0), ("b", 1), ("c", 2)]
    assert client.get(f"/api/boards/{bid}", headers=h).json()["task_count"] == 3


def test_update_fields_and_clear_due_date(client, board):
    h, bid = board
    t = client.post(
        f"/api/boards/{bid}/tasks",
        json={"title": "Write docs", "priority": "high", "due_date": "2030-01-05"},
        headers=h,
    ).json()
    r = client.patch(f"/api/tasks/{t['id']}", json={"description": "README first"}, headers=h)
    assert r.json()["description"] == "README first" and r.json()["due_date"] == "2030-01-05"
    r = client.patch(f"/api/tasks/{t['id']}", json={"clear_due_date": True}, headers=h)
    assert r.json()["due_date"] is None


def test_move_between_columns_keeps_order(client, board):
    h, bid = board
    ids = {}
    for title in ["a", "b", "c"]:
        ids[title] = client.post(
            f"/api/boards/{bid}/tasks", json={"title": title}, headers=h
        ).json()["id"]
    done = client.post(
        f"/api/boards/{bid}/tasks", json={"title": "z", "status": "done"}, headers=h
    ).json()

    # move "b" to the top of done
    r = client.post(
        f"/api/tasks/{ids['b']}/move", json={"status": "done", "position": 0}, headers=h
    )
    assert r.status_code == 200 and r.json()["status"] == "done" and r.json()["position"] == 0

    assert titles(client, h, bid, "todo") == ["a", "c"]
    assert titles(client, h, bid, "done") == ["b", "z"]

    # positions in todo were compacted
    todo = [
        t for t in client.get(f"/api/boards/{bid}/tasks", headers=h).json() if t["status"] == "todo"
    ]
    assert [t["position"] for t in todo] == [0, 1]

    # reorder inside a column: move "c" above "a"
    move = {"status": "todo", "position": 0}
    client.post(f"/api/tasks/{ids['c']}/move", json=move, headers=h)
    assert titles(client, h, bid, "todo") == ["c", "a"]

    # position beyond the end lands last
    move = {"status": "todo", "position": 99}
    client.post(f"/api/tasks/{done['id']}/move", json=move, headers=h)
    assert titles(client, h, bid, "todo") == ["c", "a", "z"]


def test_delete_compacts_positions(client, board):
    h, bid = board
    ids = [
        client.post(f"/api/boards/{bid}/tasks", json={"title": t}, headers=h).json()["id"]
        for t in "abc"
    ]
    assert client.delete(f"/api/tasks/{ids[0]}", headers=h).status_code == 204
    tasks = client.get(f"/api/boards/{bid}/tasks", headers=h).json()
    assert [(t["title"], t["position"]) for t in tasks] == [("b", 0), ("c", 1)]


def test_tasks_are_private(client, auth, board):
    h, bid = board
    other = auth("other@x.io")
    t = client.post(f"/api/boards/{bid}/tasks", json={"title": "secret"}, headers=h).json()
    assert client.get(f"/api/boards/{bid}/tasks", headers=other).status_code == 404
    assert (
        client.patch(f"/api/tasks/{t['id']}", json={"title": "hack"}, headers=other).status_code
        == 404
    )
    assert (
        client.post(
            f"/api/tasks/{t['id']}/move", json={"status": "done", "position": 0}, headers=other
        ).status_code
        == 404
    )
