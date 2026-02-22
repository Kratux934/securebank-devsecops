from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from jose import JWTError, jwt
import os
import uuid

app = FastAPI(title="SecureBank Account Service", version="1.0.0")

# Configuration JWT — même clé que auth-service
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "changeme-in-production")
ALGORITHM = "HS256"
security = HTTPBearer()

# Base de données simulée
accounts_db = {}

# --- Modèles Pydantic ---

class AccountCreate(BaseModel):
    account_type: str  # checking, savings

class Account(BaseModel):
    account_id: str
    username: str
    account_type: str
    balance: float

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
    return {"status": "healthy", "service": "account-service"}

@app.post("/accounts", status_code=status.HTTP_201_CREATED)
def create_account(
    account: AccountCreate,
    username: str = Depends(verify_token)
):
    if account.account_type not in ["checking", "savings"]:
        raise HTTPException(status_code=400, detail="Type de compte invalide")
    
    account_id = str(uuid.uuid4())
    accounts_db[account_id] = {
        "account_id": account_id,
        "username": username,
        "account_type": account.account_type,
        "balance": 0.0
    }
    return accounts_db[account_id]

@app.get("/accounts")
def get_accounts(username: str = Depends(verify_token)):
    user_accounts = [
        acc for acc in accounts_db.values()
        if acc["username"] == username
    ]
    return user_accounts

@app.get("/accounts/{account_id}")
def get_account(
    account_id: str,
    username: str = Depends(verify_token)
):
    account = accounts_db.get(account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    if account["username"] != username:
        raise HTTPException(status_code=403, detail="Accès refusé")
    return account
