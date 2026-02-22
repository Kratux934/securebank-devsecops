# 11 — Microservices SecureBank

## Objectif
Développement des 3 microservices Python FastAPI de
SecureBank — auth-service, account-service et
transaction-service — avec leurs Dockerfiles sécurisés
et leurs tests unitaires.

## Architecture microservices

### Pourquoi des microservices ?
Au lieu d'une seule application monolithique, on découpe
en services indépendants. Chaque service a son propre
rôle, son propre code, sa propre image Docker.

Avantages :
- Déploiement indépendant de chaque service
- Si account-service tombe, auth-service continue
- Mise à l'échelle indépendante selon la charge
- Standard en entreprise fintech

---

## Les 3 microservices

### auth-service (port 8001)
Gère l'authentification des utilisateurs.
- `/register` — inscription, hash le mot de passe
- `/login` — connexion, retourne un JWT
- `/verify` — vérifie qu'un JWT est valide
- `/health` — endpoint de santé pour Kubernetes

### account-service (port 8002)
Gère les comptes bancaires.
- `/accounts` POST — créer un compte
- `/accounts` GET — lister ses comptes
- `/accounts/{id}` GET — détails d'un compte
- `/health` — endpoint de santé

### transaction-service (port 8003)
Gère les transactions financières.
- `/transactions` POST — créer une transaction
- `/transactions` GET — lister ses transactions
- `/transactions/{id}` GET — détails d'une transaction
- `/health` — endpoint de santé

---

## Concept clé — JWT (JSON Web Token)

### Le problème sans JWT
Avec plusieurs microservices, chaque service devrait
appeler la base de données pour vérifier l'identité
de l'utilisateur à chaque requête — pas scalable.

### La solution JWT
```
1. Utilisateur se connecte sur auth-service
2. auth-service génère un JWT signé avec SECRET_KEY
3. Utilisateur envoie ce JWT dans chaque requête
4. Chaque service vérifie la signature localement
   sans appeler la base de données
```

### Structure d'un JWT
```
eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMjN9.abc123
       Header              Payload            Signature
```

- Header — algorithme de signature (HS256)
- Payload — données (username, expiration)
- Signature — preuve cryptographique d'authenticité

### La même SECRET_KEY sur les 3 services
C'est ce qui permet à account-service et
transaction-service de vérifier les tokens générés
par auth-service — sans avoir à communiquer entre eux.

---

## Sécurité dans le code

### Hash des mots de passe — bcrypt
```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
```
On ne stocke jamais un mot de passe en clair.
bcrypt génère un hash irréversible avec sel aléatoire.

### SECRET_KEY depuis variable d'environnement
```python
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "changeme-in-production")
```
La clé ne est jamais hardcodée dans le code.
En production elle viendra de Vault.

### Contrôle d'accès
```python
if account["username"] != username:
    raise HTTPException(status_code=403, detail="Accès refusé")
```
Un utilisateur ne peut accéder qu'à ses propres données.

### Validation métier
```python
if transaction.amount <= 0:
    raise HTTPException(status_code=400, detail="Montant invalide")
```
On valide les données métier avant tout traitement.

---

## Dockerfile sécurisé

```dockerfile
FROM python:3.11-slim

RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=appuser:appgroup main.py .

USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Choix de sécurité :**

`python:3.11-slim` — image minimale, moins de surface
d'attaque qu'une image complète.

`adduser --system` — utilisateur non-root dédié.
Si un attaquant compromet le container, il n'a pas
les droits root sur le système.

`--chown=appuser:appgroup` — les fichiers appartiennent
à appuser, pas à root.

`USER appuser` — l'application tourne sans privilèges.

`--no-cache-dir` — pas de cache pip dans l'image,
réduit la taille.

---

## Docker Compose local

```yaml
services:
  auth-service:
    build: ./app/auth-service
    ports:
      - "8001:8000"
    environment:
      - JWT_SECRET_KEY=changeme-in-development
    networks:
      - securebank-network

  account-service:
    build: ./app/account-service
    ports:
      - "8002:8000"
    environment:
      - JWT_SECRET_KEY=changeme-in-development
    networks:
      - securebank-network

  transaction-service:
    build: ./app/transaction-service
    ports:
      - "8003:8000"
    environment:
      - JWT_SECRET_KEY=changeme-in-development
    networks:
      - securebank-network

networks:
  securebank-network:
    driver: bridge
```

**`securebank-network`** — réseau Docker privé qui permet
aux 3 services de communiquer entre eux par leur nom
de container.

---

## Lancer les services en local

```bash
git clone https://github.com/Kratux934/securebank-devsecops.git
cd securebank-devsecops
docker compose up --build
```

### Vérifier que les services répondent
```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
```

Résultats attendus :
```json
{"status":"healthy","service":"auth-service"} ✅
{"status":"healthy","service":"account-service"} ✅
{"status":"healthy","service":"transaction-service"} ✅
```

---

## Tests unitaires

Chaque service a ses propres tests dans `tests/test_main.py`.

### Ce qu'on teste
- Endpoints health
- Création de ressources
- Validation des données invalides
- Contrôle d'accès (403 si mauvais utilisateur)
- Authentification (401 sans token)

### Tests de sécurité importants
- `test_register_duplicate` — pas de double inscription
- `test_login_wrong_password` — mauvais mdp = refus
- `test_get_account_wrong_user` — isolation des données
- `test_create_transaction_negative_amount` — validation métier
- `test_no_token` — sans JWT = refus

---

## Problème rencontré — docker-compose 1.29.2

### Erreur
```
KeyError: 'ContainerConfig'
```

### Cause
Incompatibilité entre docker-compose 1.29.2 (ancienne
version apt Ubuntu) et Docker Engine 28+ (nouvelle version).

### Solution
Installation de Docker CE officiel via repo HashiCorp
qui inclut docker-compose-plugin (v2.x) compatible.

```bash
sudo apt remove -y docker.io docker-compose
# Puis installation Docker CE officiel
```

---

## Statut
- [x] auth-service — code, Dockerfile, tests ✅
- [x] account-service — code, Dockerfile, tests ✅
- [x] transaction-service — code, Dockerfile, tests ✅
- [x] docker-compose.yml local ✅
- [x] 3 services démarrés et healthy ✅
- [x] Snapshot microservices-local-ready ✅
