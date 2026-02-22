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

def test_create_transaction():
    token = create_test_token("testuser")
    response = client.post("/transactions",
        json={
            "account_id": "acc-123",
            "amount": 100.0,
            "transaction_type": "deposit",
            "description": "Test deposit"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 201
    assert response.json()["amount"] == 100.0
    assert response.json()["transaction_type"] == "deposit"

def test_create_transaction_invalid_type():
    token = create_test_token("testuser")
    response = client.post("/transactions",
        json={
            "account_id": "acc-123",
            "amount": 100.0,
            "transaction_type": "invalid",
            "description": ""
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400

def test_create_transaction_negative_amount():
    token = create_test_token("testuser")
    response = client.post("/transactions",
        json={
            "account_id": "acc-123",
            "amount": -50.0,
            "transaction_type": "deposit",
            "description": ""
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 400

def test_get_transactions():
    token = create_test_token("testuser3")
    client.post("/transactions",
        json={
            "account_id": "acc-456",
            "amount": 200.0,
            "transaction_type": "withdrawal",
            "description": "Test withdrawal"
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    response = client.get("/transactions",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert len(response.json()) >= 1

def test_get_transaction_wrong_user():
    token1 = create_test_token("user1")
    token2 = create_test_token("user2")
    create_response = client.post("/transactions",
        json={
            "account_id": "acc-789",
            "amount": 300.0,
            "transaction_type": "transfer",
            "description": "Test transfer"
        },
        headers={"Authorization": f"Bearer {token1}"}
    )
    transaction_id = create_response.json()["transaction_id"]
    response = client.get(f"/transactions/{transaction_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response.status_code == 403

def test_no_token():
    response = client.get("/transactions")
    assert response.status_code == 403
