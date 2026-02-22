from fastapi.testclient import TestClient
from main import app
from jose import jwt
from datetime import datetime, timedelta
import os

client = TestClient(app)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "changeme-in-production")
ALGORITHM = "HS256"

def create_test_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=30)
    return jwt.encode({"sub": username, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_account():
    token = create_test_token("testuser")
    response = client.post("/accounts",
        json={"account_type": "checking"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    assert response.json()["account_type"] == "checking"
    assert response.json()["balance"] == 0.0

def test_create_account_invalid_type():
    token = create_test_token("testuser")
    response = client.post("/accounts",
        json={"account_type": "invalid"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400

def test_get_accounts():
    token = create_test_token("testuser2")
    client.post("/accounts",
        json={"account_type": "savings"},
        headers={"Authorization": f"Bearer {token}"}
    )
    response = client.get("/accounts",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_get_account_wrong_user():
    token1 = create_test_token("user1")
    token2 = create_test_token("user2")
    create_response = client.post("/accounts",
        json={"account_type": "checking"},
        headers={"Authorization": f"Bearer {token1}"}
    )
    account_id = create_response.json()["account_id"]
    response = client.get(f"/accounts/{account_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response.status_code == 403

def test_no_token():
    response = client.get("/accounts")
    assert response.status_code == 403
