def register_user(client, email, password="TestPassword123!"):
    return client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
        },
    )


def login_user(client, email, password="TestPassword123!"):
    # OAuth2PasswordRequestForm names the email field "username".
    response = client.post(
        "/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_registration_and_login(client):
    registration = register_user(client, "alice@example.com")

    assert registration.status_code == 201
    user_data = registration.json()
    assert user_data["email"] == "alice@example.com"
    assert "password" not in user_data
    assert "hashed_password" not in user_data

    duplicate = register_user(client, "alice@example.com")
    assert duplicate.status_code == 409

    token = login_user(client, "alice@example.com")
    assert isinstance(token, str)
    assert len(token) > 20

    wrong_password = client.post(
        "/auth/login",
        data={
            "username": "alice@example.com",
            "password": "IncorrectPassword123!",
        },
    )
    assert wrong_password.status_code == 401


def test_task_crud_requires_authentication(client):
    # Missing and malformed bearer tokens must be rejected.
    assert client.get("/tasks").status_code == 401
    assert client.get(
        "/tasks",
        headers=auth_header("not-a-valid-token"),
    ).status_code == 401

    register_user(client, "owner@example.com")
    token = login_user(client, "owner@example.com")
    headers = auth_header(token)

    created = client.post(
        "/tasks",
        headers=headers,
        json={
            "title": "Learn testing",
            "description": "Write an API test",
            "completed": False,
        },
    )
    assert created.status_code == 201
    task = created.json()
    task_id = task["id"]
    assert task["title"] == "Learn testing"

    listed = client.get("/tasks", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == task_id

    fetched = client.get(f"/tasks/{task_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Learn testing"

    updated = client.put(
        f"/tasks/{task_id}",
        headers=headers,
        json={
            "title": "Learn API testing",
            "completed": True,
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Learn API testing"
    assert updated.json()["completed"] is True

    deleted = client.delete(f"/tasks/{task_id}", headers=headers)
    assert deleted.status_code == 200

    missing_after_delete = client.get(
        f"/tasks/{task_id}",
        headers=headers,
    )
    assert missing_after_delete.status_code == 404


def test_users_cannot_access_each_others_tasks(client):
    register_user(client, "alice@example.com")
    register_user(client, "bob@example.com")

    alice_token = login_user(client, "alice@example.com")
    bob_token = login_user(client, "bob@example.com")

    alice_headers = auth_header(alice_token)
    bob_headers = auth_header(bob_token)

    created = client.post(
        "/tasks",
        headers=alice_headers,
        json={
            "title": "Alice private task",
            "description": "Bob must not access this",
            "completed": False,
        },
    )
    assert created.status_code == 201
    alice_task_id = created.json()["id"]

    # Bob's task list must not include Alice's task.
    bob_tasks = client.get("/tasks", headers=bob_headers)
    assert bob_tasks.status_code == 200
    assert all(task["id"] != alice_task_id for task in bob_tasks.json())

    # Bob cannot read, update, or delete Alice's task.
    assert client.get(
        f"/tasks/{alice_task_id}",
        headers=bob_headers,
    ).status_code == 404

    assert client.put(
        f"/tasks/{alice_task_id}",
        headers=bob_headers,
        json={"title": "Bob changed this"},
    ).status_code == 404

    assert client.delete(
        f"/tasks/{alice_task_id}",
        headers=bob_headers,
    ).status_code == 404

    # Alice's task still exists and was not changed.
    alice_task = client.get(
        f"/tasks/{alice_task_id}",
        headers=alice_headers,
    )
    assert alice_task.status_code == 200
    assert alice_task.json()["title"] == "Alice private task"