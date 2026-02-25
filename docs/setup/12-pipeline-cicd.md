# 12 — Pipeline CI/CD SecureBank

## Objectif
Construire un pipeline CI/CD complet sur GitLab qui
déclenche automatiquement à chaque push :
tests unitaires → build images Docker → push sur Harbor.

---

## Architecture du pipeline

```
Push code sur GitLab
        ↓
Stage 1 : test
├── test-auth      (pytest)
├── test-account   (pytest)
└── test-transaction (pytest)
        ↓
Stage 2 : build
├── build-auth      (docker build)
├── build-account   (docker build)
└── build-transaction (docker build)
        ↓
Stage 3 : push
├── push-auth      (docker push → Harbor)
├── push-account   (docker push → Harbor)
└── push-transaction (docker push → Harbor)
```

---

## Prérequis

- GitLab CE installé sur vm-gitlab (192.168.157.10)
- Harbor installé sur vm-security (192.168.157.20)
- Docker CE installé sur vm-gitlab
- GitLab Runner enregistré et actif

---

## 1. Configuration du GitLab Runner

### Problème rencontré — Runner offline
Le Runner avait perdu son enregistrement car la config
était dans `/home/hicham/.gitlab-runner/config.toml`
au lieu de `/etc/gitlab-runner/config.toml`.

**Cause** : L'enregistrement avait été fait sans `sudo`
ce qui écrit la config dans le dossier de l'utilisateur
courant au lieu du dossier système.

**Règle** : Toujours utiliser `sudo gitlab-runner register`
pour que la config soit écrite dans `/etc/gitlab-runner/`.

### Ré-enregistrement du Runner

Sur GitLab → Admin → CI/CD → Runners → New instance runner :
- Tags : `docker,linux,securebank`
- Run untagged jobs : ✅
- Description : `securebank-runner`

```bash
sudo gitlab-runner register \
  --url http://192.168.157.10 \
  --token VOTRE_TOKEN \
  --executor docker \
  --docker-image docker:24.0 \
  --description securebank-runner
```

### Correction config.toml — privileged et socket

```bash
sudo nano /etc/gitlab-runner/config.toml
```

```toml
concurrent = 4
check_interval = 0
shutdown_timeout = 0

[session_server]
  session_timeout = 1800

[[runners]]
  name = "securebank-runner"
  url = "http://192.168.157.10"
  executor = "docker"
  [runners.docker]
    tls_verify = false
    image = "docker:24.0"
    privileged = true
    disable_entrypoint_overwrite = false
    oom_kill_disable = false
    disable_cache = false
    volumes = ["/cache", "/var/run/docker.sock:/var/run/docker.sock"]
    shm_size = 0
    network_mtu = 0
```

**Points importants :**

`concurrent = 4` — permet au Runner de prendre 4 jobs
en parallèle. Par défaut c'est 1 — les jobs s'exécutent
un par un ce qui est très lent.

`privileged = true` — nécessaire pour Docker-in-Docker.

`/var/run/docker.sock:/var/run/docker.sock` — monte le
socket Docker de vm-gitlab dans les containers des jobs.
Permet aux jobs d'utiliser le Docker de la VM hôte
directement sans DinD.

```bash
sudo systemctl enable gitlab-runner
sudo systemctl restart gitlab-runner
```

---

## 2. Docker socket vs Docker-in-Docker (DinD)

### Docker-in-Docker (DinD)
Lance un container Docker à l'intérieur du container
du Runner. Nécessite privileged=true et une configuration
précise avec `DOCKER_HOST` et `DOCKER_TLS_CERTDIR`.

```
VM gitlab
└── Container Runner
    └── Container Docker (DinD)
        └── docker build → image créée
```

### Docker socket
Monte le socket Docker de vm-gitlab dans le container
du Runner. Plus simple, plus fiable pour un lab.

```
VM gitlab
├── Docker daemon
└── Container Runner
    └── /var/run/docker.sock (monté)
        └── Docker daemon de vm-gitlab
            └── docker build/push ✅
```

**Pour notre lab** : on utilise le socket pour les jobs
push car DinD posait des problèmes de connectivité.
Les jobs build utilisent DinD avec `services: docker:dind`.

---

## 3. Harbor comme registry insecure

Harbor tourne en HTTP (pas HTTPS) dans notre lab.
Docker refuse par défaut les connexions non-sécurisées.

### Configuration sur vm-gitlab

```bash
sudo nano /etc/docker/daemon.json
```

```json
{"insecure-registries":["192.168.157.20"]}
```

```bash
sudo systemctl stop docker
sudo systemctl stop docker.socket
sudo systemctl start docker
```

Vérification :
```bash
docker info | grep -A5 "Insecure"
# Doit afficher : 192.168.157.20
```

---

## 4. Synchronisation GitHub → GitLab

### Contexte
GitLab CE ne supporte pas le Pull mirroring (disponible
uniquement sur GitLab EE/Enterprise). On synchronise
manuellement depuis vm-gitlab.

### GitLab EE — Pull mirror automatique
Settings → Repository → Mirroring repositories :
- URL : `https://github.com/username/repo.git`
- Direction : **Pull**
- Auth : Username + Personal Access Token GitHub

### GitLab CE — Push manuel

**Création du token GitLab** :
GitLab → Avatar → Edit profile → Access Tokens
- Name : `git-push`
- Scopes : `api`, `write_repository`

**Autoriser le force push sur main** :
Settings → Repository → Protected branches → main
→ Allowed to force push : ✅

**Commandes de synchronisation** :
```bash
cd ~/securebank-devsecops
git remote add gitlab http://root@192.168.157.10/root/securebank.git
git pull origin main && git push gitlab main --force
```

**À faire après chaque modification sur GitHub.**

---

## 5. Variables CI/CD secrètes

Sur GitLab → projet securebank → Settings → CI/CD → Variables

| Key | Value | Visibility |
|-----|-------|------------|
| HARBOR_USERNAME | admin | Masked and hidden |
| HARBOR_PASSWORD | votre_mdp_harbor | Masked and hidden |

**Masked and hidden** — la valeur n'apparaît jamais
dans les logs du pipeline ni dans l'interface GitLab.
Indispensable pour les credentials en fintech.

---

## 6. Le fichier .gitlab-ci.yml complet

```yaml
stages:
  - test
  - build
  - push

variables:
  HARBOR_URL: "192.168.157.20"
  HARBOR_PROJECT: "securebank"
  DOCKER_HOST: tcp://docker:2375
  DOCKER_TLS_CERTDIR: ""

test-auth:
  stage: test
  image: python:3.11-slim
  before_script:
    - pip install -r app/auth-service/requirements.txt
  script:
    - cd app/auth-service
    - PYTHONPATH=. pytest tests/ -v

test-account:
  stage: test
  image: python:3.11-slim
  before_script:
    - pip install -r app/account-service/requirements.txt
  script:
    - cd app/account-service
    - PYTHONPATH=. pytest tests/ -v

test-transaction:
  stage: test
  image: python:3.11-slim
  before_script:
    - pip install -r app/transaction-service/requirements.txt
  script:
    - cd app/transaction-service
    - PYTHONPATH=. pytest tests/ -v

build-auth:
  stage: build
  image: docker:24.0
  services:
    - name: docker:24.0-dind
      alias: docker
  script:
    - sleep 5
    - docker build -t $HARBOR_URL/$HARBOR_PROJECT/auth-service:$CI_COMMIT_SHORT_SHA app/auth-service/

build-account:
  stage: build
  image: docker:24.0
  services:
    - name: docker:24.0-dind
      alias: docker
  script:
    - sleep 5
    - docker build -t $HARBOR_URL/$HARBOR_PROJECT/account-service:$CI_COMMIT_SHORT_SHA app/account-service/

build-transaction:
  stage: build
  image: docker:24.0
  services:
    - name: docker:24.0-dind
      alias: docker
  script:
    - sleep 5
    - docker build -t $HARBOR_URL/$HARBOR_PROJECT/transaction-service:$CI_COMMIT_SHORT_SHA app/transaction-service/

push-auth:
  stage: push
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
  script:
    - docker build -t $HARBOR_URL/$HARBOR_PROJECT/auth-service:$CI_COMMIT_SHORT_SHA app/auth-service/
    - echo "$HARBOR_PASSWORD" | docker login $HARBOR_URL -u $HARBOR_USERNAME --password-stdin
    - docker push $HARBOR_URL/$HARBOR_PROJECT/auth-service:$CI_COMMIT_SHORT_SHA

push-account:
  stage: push
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
  script:
    - docker build -t $HARBOR_URL/$HARBOR_PROJECT/account-service:$CI_COMMIT_SHORT_SHA app/account-service/
    - echo "$HARBOR_PASSWORD" | docker login $HARBOR_URL -u $HARBOR_USERNAME --password-stdin
    - docker push $HARBOR_URL/$HARBOR_PROJECT/account-service:$CI_COMMIT_SHORT_SHA

push-transaction:
  stage: push
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
  script:
    - docker build -t $HARBOR_URL/$HARBOR_PROJECT/transaction-service:$CI_COMMIT_SHORT_SHA app/transaction-service/
    - echo "$HARBOR_PASSWORD" | docker login $HARBOR_URL -u $HARBOR_USERNAME --password-stdin
    - docker push $HARBOR_URL/$HARBOR_PROJECT/transaction-service:$CI_COMMIT_SHORT_SHA
```

---

## 7. Concepts clés du pipeline

### Stages et Jobs
**Stage** — une étape du pipeline. Les stages s'exécutent
séquentiellement — le stage build ne démarre que si
tous les jobs du stage test sont passés.

**Job** — une tâche dans un stage. Les jobs d'un même
stage s'exécutent en parallèle.

### Variables automatiques GitLab
`$CI_COMMIT_SHORT_SHA` — les 8 premiers caractères du
hash du commit. Exemple : `2b4184ff`. Permet de tracer
quelle image correspond à quel commit — critique en
fintech pour l'audit et le rollback.

### PYTHONPATH
```bash
PYTHONPATH=. pytest tests/ -v
```
Dit à Python de chercher les modules dans le dossier
courant. Sans ça pytest ne trouve pas `main.py` car
il cherche depuis le dossier `tests/`.

### before_script vs script
`before_script` — s'exécute avant le script principal,
dans le même contexte. Utilisé pour les installations
de dépendances.

`script` — les commandes principales du job.

---

## 8. Problèmes rencontrés et solutions

### Problème 1 — bcrypt incompatible
**Erreur** : `ValueError: password cannot be longer than 72 bytes`

**Cause** : passlib 1.7.4 cherche `bcrypt.__about__.__version__`
mais les versions récentes de bcrypt ont supprimé cet attribut.

**Solution** : Fixer `bcrypt==4.0.1` dans requirements.txt.

### Problème 2 — ModuleNotFoundError: No module named 'main'
**Cause** : pytest exécuté depuis `tests/` ne trouve pas
`main.py` dans le dossier parent.

**Solution** : `PYTHONPATH=. pytest tests/ -v`

### Problème 3 — Cannot connect to Docker daemon
**Cause** : Variable globale `DOCKER_HOST: tcp://docker:2375`
s'appliquait aux jobs push qui n'utilisent pas DinD.

**Solution** : Surcharger dans les jobs push :
`DOCKER_HOST: "unix:///var/run/docker.sock"`

### Problème 4 — Harbor connexion refusée (HTTPS)
**Cause** : Docker essaie de se connecter en HTTPS sur
le port 443 alors que Harbor tourne en HTTP port 80.

**Solution** : Ajouter Harbor comme insecure registry
dans `/etc/docker/daemon.json` sur vm-gitlab.

### Problème 5 — client version too old
**Erreur** : `client version 1.43 is too old. Minimum supported API version is 1.44`

**Cause** : Image `docker:24.0` trop ancienne par rapport
au daemon Docker de vm-gitlab.

**Solution** : Utiliser `docker:27.0` pour les jobs push.

### Problème 6 — Branch protégée
**Erreur** : `You are not allowed to force push code to a protected branch`

**Solution** : Settings → Repository → Protected branches
→ main → Allowed to force push : ✅

---

## 9. Vérification finale

Sur Harbor → http://192.168.157.20 → projet securebank
→ Repositories — tu dois voir 3 repositories :
- securebank/auth-service
- securebank/account-service
- securebank/transaction-service

Chaque repository contient une image taguée avec le
hash du commit — ex: `2b4184ff`.

---

## Statut
- [x] Runner enregistré et configuré ✅
- [x] Docker socket monté ✅
- [x] Harbor insecure registry configuré ✅
- [x] Variables secrètes Harbor dans GitLab ✅
- [x] Stage test — 3 jobs pytest ✅
- [x] Stage build — 3 images Docker ✅
- [x] Stage push — 3 images sur Harbor ✅
- [x] Snapshot pipeline-ci-ready ✅

---

## Prochaine étape — Phase 4
Supply chain security :
- Trivy — scan de vulnérabilités des images
- Syft — génération de SBOM
- OWASP Dependency-Track — suivi continu
- Cosign — signature des images
