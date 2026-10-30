def test_board_crud(client, auth):
    h = auth()
    r = client.post("/api/boards", json={"name": "  Launch  "}, headers=h)
    assert r.status_code == 201
    board = r.json()
    assert board["name"] == "Launch" and board["task_count"] == 0

    r = client.patch(f"/api/boards/{board['id']}", json={"name": "Launch v2"}, headers=h)
    assert r.json()["name"] == "Launch v2"

    assert [b["id"] for b in client.get("/api/boards", headers=h).json()] == [board["id"]]
    assert client.delete(f"/api/boards/{board['id']}", headers=h).status_code == 204
    assert client.get("/api/boards", headers=h).json() == []


def test_boards_are_private(client, auth):
    ann, bob = auth("ann@x.io"), auth("bob@x.io")
    board = client.post("/api/boards", json={"name": "Ann's"}, headers=ann).json()
    assert client.get(f"/api/boards/{board['id']}", headers=bob).status_code == 404
    assert client.delete(f"/api/boards/{board['id']}", headers=bob).status_code == 404
    assert client.get("/api/boards", headers=bob).json() == []


def test_deleting_board_removes_tasks(client, auth):
    h = auth()
    board = client.post("/api/boards", json={"name": "B"}, headers=h).json()
    task = client.post(f"/api/boards/{board['id']}/tasks", json={"title": "t"}, headers=h).json()
    client.delete(f"/api/boards/{board['id']}", headers=h)
    assert (
        client.patch(f"/api/tasks/{task['id']}", json={"title": "x"}, headers=h).status_code == 404
    )
