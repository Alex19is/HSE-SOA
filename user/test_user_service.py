import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from user_service import app, get_db
import models

@pytest.fixture(scope="function")
def db():
    db = SessionLocal()
    try:
        yield db 
    finally:
        db.close()  

@pytest.fixture(scope="session", autouse=True)
def clean_db_after_tests():
    yield  
    db = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()  
    finally:
        db.close()  

@pytest.fixture(scope="function")
def client(db):
    return TestClient(app)

def test_create_user(client):
    response = client.post("/users/", json={
        "login": "testus",
        "email": "test@exam.com",
        "password": "securepassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["login"] == "testus"
    assert data["email"] == "test@exam.com"

def test_login(client):
    response = client.post("/token", json={
        "login": "testus",
        "password": "securepassword"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

def test_read_users_me(client):
    login_response = client.post("/token", json={
        "login": "testus",
        "password": "securepassword"
    })
    token = login_response.json()["access_token"]

    response = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["login"] == "testus"

def test_update_first_name(client):
    login_response = client.post("/token", json={
        "login": "testus",
        "password": "securepassword"
    })
    token = login_response.json()["access_token"]

    response = client.put("/users/me/first_name", json={"first_name": "John"}, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["message"] == "First name updated successfully"
