from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

app = FastAPI(title="SecureBank Auth Service", version="1.0.0")

# Configuration JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "changeme-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Hachage des mots de passe
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Base de données simulée (sera remplacée par PostgreSQL)
fake_db = {}

# --- Modèles Pydantic ---

class UserRegister(BaseModel):
    username: str
    password: str
    email: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# --- Fonctions utilitaires ---

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

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
    return {"status": "healthy", "service": "auth-service"}

@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(user: UserRegister):
    if user.username in fake_db:
        raise HTTPException(status_code=400, detail="Utilisateur déjà existant")
    fake_db[user.username] = {
        "username": user.username,
        "email": user.email,
        "password": hash_password(user.password)
    }
    return {"message": "Utilisateur créé avec succès"}

@app.post("/login", response_model=Token)
def login(user: UserLogin):
    db_user = fake_db.get(user.username)
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/verify")
def verify(username: str = Depends(verify_token)):
    return {"username": username, "valid": True}
