import requests
import uuid

# Адреса сервисов (предполагаем, что:
#  - user-service запущен на http://localhost:8000
#  - шлюз (gateway) запущен на http://localhost:8001)
USER_SERVICE_URL = "http://localhost:8000"
GATEWAY_URL = "http://localhost:8001"


def register_user():
    """
    Регистрирует нового пользователя с уникальным login.
    Возвращает сгенерированный login.
    """
    login = f"user_{uuid.uuid4().hex[:8]}"
    payload = {
        "login": login,
        "email": f"{login}@example.com",
        "password": "password"
    }
    resp = requests.post(f"{USER_SERVICE_URL}/users/", json=payload)
    assert resp.status_code == 200, f"Registration failed: {resp.status_code} – {resp.text}"
    return login


def get_token(login: str) -> str:
    """
    Получает JWT-токен для указанного login.
    """
    resp = requests.post(
        f"{USER_SERVICE_URL}/token",
        json={"login": login, "password": "password"}
    )
    assert resp.status_code == 200, f"Login failed: {resp.status_code} – {resp.text}"
    return resp.json()["access_token"]


def test_create_and_get_post():
    """
    Сценарий:
      1. Регистрируем пользователя.
      2. Получаем для него токен.
      3. Через gateway создаём новый публичный пост.
      4. Через gateway запрашиваем только что созданный пост по ID и проверяем поля.
    """
    # 1. Регистрация и авторизация
    login = register_user()
    token = get_token(login)
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Создаём пост через gateway
    post_payload = {
        "title": "Test Post",
        "description": "Описание тестового поста",
        "is_private": False,
        "tags": ["tag1", "tag2"]
    }
    resp = requests.post(f"{GATEWAY_URL}/posts", json=post_payload, headers=headers)
    assert resp.status_code == 200, f"Create post failed: {resp.status_code} – {resp.text}"
    post = resp.json()
    post_id = post["id"]
    assert post["title"] == "Test Post"
    assert post["description"] == "Описание тестового поста"
    assert post["creator"] == login

    # 3. Получаем пост по ID через gateway
    resp = requests.get(f"{GATEWAY_URL}/posts/{post_id}", headers=headers)
    assert resp.status_code == 200, f"Get post failed: {resp.status_code} – {resp.text}"
    retrieved = resp.json()
    assert retrieved["id"] == post_id
    assert retrieved["title"] == "Test Post"
    assert retrieved["description"] == "Описание тестового поста"


def test_like_and_comment_flow():
    """
    Сценарий:
      1. Регистрируем пользователя.
      2. Получаем JWT.
      3. Создаём новый публичный пост.
      4. Ставим лайк этому посту.
      5. Добавляем комментарий к посту.
      6. Запрашиваем список комментариев и проверяем, что наш комментарий есть.
    """
    # 1. Регистрация и авторизация
    login = register_user()
    token = get_token(login)
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Создаём пост через gateway
    post_payload = {
        "title": "Another Post",
        "description": "Еще один тестовый пост",
        "is_private": False,
        "tags": []
    }
    resp = requests.post(f"{GATEWAY_URL}/posts", json=post_payload, headers=headers)
    assert resp.status_code == 200, f"Create post failed: {resp.status_code} – {resp.text}"
    post_id = resp.json()["id"]

    # 3. Лайкаем пост
    resp = requests.post(f"{GATEWAY_URL}/posts/{post_id}/like", headers=headers)
    assert resp.status_code == 200, f"Like post failed: {resp.status_code} – {resp.text}"
    like_result = resp.json()
    assert like_result["total_likes"] == 1

    # 4. Добавляем комментарий
    comment_payload = {"text": "Отличный пост!"}
    resp = requests.post(f"{GATEWAY_URL}/posts/{post_id}/comments", json=comment_payload, headers=headers)
    assert resp.status_code == 200, f"Comment post failed: {resp.status_code} – {resp.text}"
    comment = resp.json()
    assert comment["text"] == "Отличный пост!"
    comment_id = comment["id"]

    # 5. Получаем список комментариев
    resp = requests.get(f"{GATEWAY_URL}/posts/{post_id}/comments", headers=headers)
    assert resp.status_code == 200, f"List comments failed: {resp.status_code} – {resp.text}"
    comments = resp.json()
    assert any(c["id"] == comment_id for c in comments), "Комментарий не найден в списке"


def test_post_creation_like_view_flow():
    """
    Сценарий:
      1. Пользователь A создаёт пост.
      2. Пользователь B лайкает пост A.
      3. Пользователь B просматривает пост A.
      4. Проверяем, что пост доступен и содержит нужные поля.
    """
    # A создаёт пост
    login_a = register_user()
    token_a = get_token(login_a)
    headers_a = {"Authorization": f"Bearer {token_a}"}

    post_payload = {
        "title": "Test post for like and view",
        "description": "Just a test",
        "is_private": False,
        "tags": []
    }
    resp = requests.post(f"{GATEWAY_URL}/posts", json=post_payload, headers=headers_a)
    assert resp.status_code == 200, f"Failed to create post: {resp.status_code} – {resp.text}"
    post_id = resp.json()["id"]

    # B лайкает и просматривает
    login_b = register_user()
    token_b = get_token(login_b)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    like_resp = requests.post(f"{GATEWAY_URL}/posts/{post_id}/like", headers=headers_b)
    assert like_resp.status_code == 200, f"Failed to like post: {like_resp.status_code} – {like_resp.text}"

    view_resp = requests.get(f"{GATEWAY_URL}/posts/{post_id}", headers=headers_b)
    assert view_resp.status_code == 200, f"Failed to view post: {view_resp.status_code} – {view_resp.text}"
    data = view_resp.json()
    assert data["id"] == post_id
    assert data["title"] == "Test post for like and view"



