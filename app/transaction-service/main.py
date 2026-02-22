from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
import os
import uuid
from datetime import datetime

app = FastAPI(title="SecureBank Transaction Service", version="1.0.0")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "changeme-in-production")
ALGORITHM = "HS256"
security = HTTPBearer()

# Base de données simulée
transactions_db = {}

# --- Modèles Pydantic ---

class TransactionCreate(BaseModel):
    account_id: str
    amount: float
    transaction_type: str  # deposit, withdrawal, transfer
    description: str = ""

class Transaction(BaseModel):
    transaction_id: str
    account_id: str
    username: str
    amount: float
    transaction_type: str
    description: str
    created_at: str

# --- Fonctions utilitaires ---

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Token invalide")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

# --- Endpoints ---

@app.get("/health")
def health():
    return {"status": "healthy", "service": "transaction-service"}

@app.post("/transactions", status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction: TransactionCreate,
    username: str = Depends(verify_token)
):
    if transaction.transaction_type not in ["deposit", "withdrawal", "transfer"]:
        raise HTTPException(status_code=400, detail="Type de transaction invalide")

    if transaction.amount <= 0:
        raise HTTPException(status_code=400, detail="Le montant doit être positif")

    transaction_id = str(uuid.uuid4())
    transactions_db[transaction_id] = {
        "transaction_id": transaction_id,
        "account_id": transaction.account_id,
        "username": username,
        "amount": transaction.amount,
        "transaction_type": transaction.transaction_type,
        "description": transaction.description,
        "created_at": datetime.utcnow().isoformat()
    }
    return transactions_db[transaction_id]

@app.get("/transactions")
def get_transactions(username: str = Depends(verify_token)):
    user_transactions = [
        t for t in transactions_db.values()
        if t["username"] == username
    ]
    return user_transactions

@app.get("/transactions/{transaction_id}")
def get_transaction(
    transaction_id: str,
    username: str = Depends(verify_token)
):
    transaction = transactions_db.get(transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction introuvable")
    if transaction["username"] != username:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return transaction
