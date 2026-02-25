from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_register():
    response = client.post("/register", json={
        "username": "testuser",
        "password": "Test1234!",
        "email": "test@securebank.com"
    })
    assert response.status_code == 201
    assert response.json()["message"] == "Utilisateur créé avec succès"

def test_register_duplicate():
    client.post("/register", json={
        "username": "dupuser",
        "password": "Test1234!",
        "email": "dup@securebank.com"
    })
    response = client.post("/register", json={
        "username": "dupuser",
        "password": "Test1234!",
        "email": "dup@securebank.com"
    })
    assert response.status_code == 400

def test_login():
    client.post("/register", json={
        "username": "loginuser",
        "password": "Test1234!",
        "email": "login@securebank.com"
    })
    response = client.post("/login", json={
        "username": "loginuser",
        "password": "Test1234!"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_wrong_password():
    response = client.post("/login", json={
        "username": "loginuser",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_verify_token():
    client.post("/register", json={
        "username": "verifyuser",
        "password": "Test1234!",
        "email": "verify@securebank.com"
    })
    login_response = client.post("/login", json={
        "username": "verifyuser",
        "password": "Test1234!"
    })
    token = login_response.json()["access_token"]
    response = client.get("/verify", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    assert response.json()["valid"] == True
