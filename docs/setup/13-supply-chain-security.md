# 13 — Supply Chain Security — Phase 4

## Objectif
Sécuriser la chaîne d'approvisionnement logicielle en
ajoutant 4 outils au pipeline CI/CD :
- **Trivy** — scan de vulnérabilités des images Docker
- **Syft** — génération de SBOM (Software Bill of Materials)
- **OWASP Dependency-Track** — surveillance continue des vulnérabilités
- **Cosign + Vault Transit** — signature cryptographique des images

---

## C'est quoi la Supply Chain Security ?

Quand tu construis une image Docker tu n'écris pas tout
de zéro. Tu utilises :
- Une image de base `python:3.11-slim` — code tiers
- Des dépendances `fastapi`, `passlib` — code tiers

Le risque : une de ces dépendances peut contenir une
vulnérabilité connue qu'un attaquant peut exploiter.

```
Pipeline après Phase 4 :
test → build → scan (Trivy) → push → sign (Cosign) → sbom (Syft) → dtrack
```

---

## 1. Trivy — Scan de vulnérabilités

### C'est quoi Trivy ?
Trivy compare le contenu de l'image Docker contre une
base de données de vulnérabilités CVE. Il identifie
précisément quelle dépendance a un problème et quelle
version corriger.

### Trivy dans le pipeline vs Trivy dans Harbor

**Trivy dans Harbor** — scan automatique à chaque push,
interface visuelle, mais le pipeline ne peut pas bloquer.

**Trivy dans le pipeline** — intégré dans le flux CI/CD,
peut bloquer si vulnérabilité critique, résultats
traçables par commit.

**Notre choix** — les deux ! Pipeline pour bloquer les
déploiements dangereux, Harbor pour la surveillance
continue. En Phase 8 Grafana unifiera les métriques.

### Job Trivy dans .gitlab-ci.yml

```yaml
scan-auth:
  stage: scan
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
  script:
    - docker build -t $HARBOR_URL/$HARBOR_PROJECT/auth-service:$CI_COMMIT_SHORT_SHA app/auth-service/
    - docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --exit-code 0 --severity HIGH,CRITICAL $HARBOR_URL/$HARBOR_PROJECT/auth-service:$CI_COMMIT_SHORT_SHA
  allow_failure: true
```

**`--exit-code 0`** — Trivy retourne toujours 0, ne bloque
pas le pipeline. En Phase 6 on mettra `--exit-code 1`
pour bloquer si vulnérabilités critiques.

**`--severity HIGH,CRITICAL`** — on ne s'intéresse qu'aux
vulnérabilités graves.

**`allow_failure: true`** — le pipeline continue même si
Trivy trouve des problèmes. À enlever en Phase 6.

**`docker run --rm`** — Trivy tourne dans un container
éphémère détruit après exécution. Rien n'est installé
sur vm-gitlab.

### Lire le rapport Trivy

```
Report Summary
┌─────────────────────────────┬────────────┬─────────────────┬─────────┐
│ Target                      │ Type       │ Vulnerabilities │ Secrets │
├─────────────────────────────┼────────────┼─────────────────┼─────────┤
│ account-service (debian)    │ debian     │ 2               │ -       │
│ ecdsa-0.19.1 (METADATA)     │ python-pkg │ 1               │ -       │
│ python-jose-3.3.0 (METADATA)│ python-pkg │ 1               │ -       │
└─────────────────────────────┴────────────┴─────────────────┴─────────┘
```

**Target** — l'élément précis scanné (OS ou package Python).
**Type** — catégorie : `debian` pour l'OS, `python-pkg`
pour les packages pip.
**Vulnerabilities** — nombre de CVE trouvées.
**Secrets** — Trivy cherche aussi les secrets hardcodés.

### Vulnérabilités trouvées sur nos images

**OS — Debian 13.3 (2 vulnérabilités HIGH)**
- `libc-bin` / `libc6` — CVE-2026-0861 — pas de fix disponible
- Risque accepté — composant de base de l'OS

**Python packages (6 vulnérabilités)**

| Package | CVE | Sévérité | Fix |
|---------|-----|----------|-----|
| python-jose 3.3.0 | CVE-2024-33663 | CRITICAL | 3.4.0 |
| ecdsa 0.19.1 | CVE-2024-23342 | HIGH | pas de fix |
| starlette 0.38.6 | CVE-2024-47874 | HIGH | 0.40.0 |
| wheel 0.45.1 | CVE-2026-24049 | HIGH | 0.46.2 |
| jaraco.context 5.3.0 | CVE-2026-23949 | HIGH | 6.1.0 |

**Actions prévues en Phase 6** : mettre à jour
`python-jose==3.4.0` et `starlette==0.40.0`.

### Faux positifs vs Vrais positifs vs Risque accepté

**Faux positif** — l'outil signale une vulnérabilité
qui n'est pas applicable dans notre contexte.
Exemple : CVE sur upload de fichiers multipart alors
que notre service ne fait que du JSON.

**Vrai positif** — la vulnérabilité est réelle et
notre code utilise la fonctionnalité vulnérable.
Exemple : python-jose CRITICAL — on utilise JWT.

**Risque accepté** — vulnérabilité réelle mais acceptée
consciemment avec justification documentée.
Exemple : libc-bin — pas de fix disponible, composant OS.

---

## 2. Syft — Génération de SBOM

### C'est quoi un SBOM ?
SBOM = Software Bill of Materials = liste d'ingrédients
complète de ton image Docker. Tous les packages OS,
toutes les librairies Python, leurs versions exactes.

### Pourquoi le SBOM ?
Trivy scanne au moment du build — photo à un instant T.
Une nouvelle CVE peut apparaître 6 mois après sur un
package déjà en production. Le SBOM permet à OWASP DT
de surveiller en continu.

### Format CycloneDX
Standard industrie reconnu par OWASP DT, GitHub,
AWS Inspector. Format JSON avec tous les composants
et leurs métadonnées.

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.6",
  "serialNumber": "urn:uuid:...",
  "components": [
    {
      "name": "fastapi",
      "version": "0.115.0",
      "type": "library"
    }
  ]
}
```

Le fichier est **minifié** (tout sur une ligne) — fait
pour être lu par des machines, pas des humains.
Pour le lire : `cat sbom.json | python3 -m json.tool`

### Job Syft dans .gitlab-ci.yml

```yaml
sbom-auth:
  stage: sbom
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
  script:
    - docker run --rm -v /var/run/docker.sock:/var/run/docker.sock anchore/syft:latest $HARBOR_URL/$HARBOR_PROJECT/auth-service:$CI_COMMIT_SHORT_SHA -o cyclonedx-json > auth-service-sbom.json
  artifacts:
    paths:
      - auth-service-sbom.json
    expire_in: 30 days
  allow_failure: true
```

**`artifacts`** — GitLab sauvegarde le fichier SBOM 30 jours.
Téléchargeable depuis l'interface GitLab.

**`anchore/syft:latest`** — comme Trivy, Syft tourne dans
un container éphémère. Rien n'est installé sur vm-gitlab.

---

## 3. OWASP Dependency-Track

### C'est quoi OWASP DT ?
Reçoit les SBOMs et surveille en continu. Dès qu'une
nouvelle CVE apparaît sur un package de tes images,
tu reçois une alerte automatique.

### Configuration des permissions

Le token API doit avoir ces permissions :
- `PROJECT_CREATION_UPLOAD` ✅
- `BOM_UPLOAD` ✅
- `VIEW_PORTFOLIO` ✅
- `VIEW_VULNERABILITY` ✅

**Administration** → **Access Management** → **Teams**
→ **Automation** → ajouter les permissions.

### Job OWASP DT dans .gitlab-ci.yml

```yaml
dtrack-auth:
  stage: dtrack
  image: python:3.11-slim
  script:
    - pip install requests
    - |
      python3 << EOF
      import requests, base64

      with open("auth-service-sbom.json", "r") as f:
          sbom_content = f.read()

      encoded = base64.b64encode(sbom_content.encode()).decode()

      payload = {
          "projectName": "auth-service",
          "projectVersion": "$CI_COMMIT_SHORT_SHA",
          "autoCreate": True,
          "bom": encoded
      }

      response = requests.put(
          "http://192.168.157.20:8080/api/v1/bom",
          headers={
              "X-Api-Key": "$DTRACK_API_KEY",
              "Content-Type": "application/json"
          },
          json=payload
      )
      print("Status:", response.status_code)
      EOF
  dependencies:
    - sbom-auth
  allow_failure: true
```

**`dependencies: sbom-auth`** — récupère automatiquement
l'artifact SBOM du job sbom-auth. Sans ça le fichier
JSON n'est pas disponible dans ce job.

**`autoCreate: True`** — crée le projet dans OWASP DT
automatiquement s'il n'existe pas.

**`base64`** — OWASP DT attend le SBOM encodé en base64.

**`projectVersion: $CI_COMMIT_SHORT_SHA`** — chaque push
crée une nouvelle version dans OWASP DT — traçabilité
complète.

### Onglets OWASP DT et leur utilité

**Audit Vulnerabilities** — triage des CVE :
vrai positif → ticket de correction,
faux positif → documenter et supprimer,
risque accepté → noter avec date de révision.

**Exploit Prediction** — priorise les CVE selon la
probabilité d'exploitation active.

**Policy Violation** — règles automatiques :
"aucune CVE Critical non corrigée depuis 30 jours".

**Dependency Graph** — visualise les dépendances
transitives.

**Notifications** — à configurer en Phase 8 :
email/Slack quand nouvelle CVE Critical détectée.

### Pourquoi Trivy et OWASP DT ?

```
Trivy    → meilleur détection CVE Python pip (temps réel)
OWASP DT → meilleur surveillance continue OS + alertes
```

Les deux sont complémentaires.

---

## 4. Cosign + Vault Transit — Signature des images

### C'est quoi Cosign ?
Outil de signature cryptographique des images Docker.
Prouve qu'une image vient bien de notre pipeline et
n'a pas été modifiée après le build.

### Méthode lab vs Méthode enterprise

**Méthode lab** — clés générées localement, stockées
dans GitLab comme variables secrètes. Acceptable pour
apprendre mais pas pour la production.

**Méthode enterprise (notre choix)** — Vault Transit
garde la clé privée. Le pipeline demande à Vault de
signer — la clé ne quitte jamais Vault.

```
Phase 4 (lab) → Vault Transit ✅ méthode pro
Phase 5 (AWS) → AWS KMS ✅ méthode cloud enterprise
```

### Vault Transit — concept

```
Pipeline : "Vault, signe moi ce hash d'image"
        ↓
Vault Transit signe en interne
        ↓
Vault retourne UNIQUEMENT la signature
        ↓
Clé privée ne quitte jamais Vault ✅
```

### Configuration Vault Transit

**1. Activer le moteur Transit**
```bash
vault secrets enable transit
```

**2. Créer la clé de signature**
```bash
vault write -f transit/keys/cosign-key type=ecdsa-p256
```

`ecdsa-p256` — algorithme utilisé par Cosign.
`exportable: false` — clé privée jamais exportable ✅

**3. Créer la politique**
```bash
vault policy write cosign-policy - << EOF
path "transit/sign/cosign-key" {
  capabilities = ["update"]
}
path "transit/sign/cosign-key/*" {
  capabilities = ["update"]
}
path "transit/keys/cosign-key" {
  capabilities = ["read"]
}
EOF
```

**`transit/sign/cosign-key/*`** — le `*` est important !
Cosign appelle `/transit/sign/cosign-key/sha2-256` —
sans le wildcard la politique refuse la requête.

**4. Créer le token**
```bash
vault token create -policy=cosign-policy -ttl=720h
```

### Clé publique dans le repo

La clé publique est exportée et stockée dans `cosign.pub`
à la racine du repo. Elle servira à Kyverno en Phase 6
pour vérifier les signatures au déploiement Kubernetes.

```bash
vault read transit/keys/cosign-key
# Copier le champ public_key
```

### Job Cosign dans .gitlab-ci.yml

```yaml
sign-auth:
  stage: sign
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
    VAULT_ADDR: "http://192.168.157.30:8200"
    VAULT_TOKEN: "$VAULT_SIGNING_TOKEN"
  script:
    - apk add --no-cache curl
    - curl -LO https://github.com/sigstore/cosign/releases/download/v2.2.0/cosign-linux-amd64
    - chmod +x cosign-linux-amd64
    - mv cosign-linux-amd64 /usr/local/bin/cosign
    - echo "$HARBOR_PASSWORD" | docker login $HARBOR_URL -u $HARBOR_USERNAME --password-stdin
    - export COSIGN_EXPERIMENTAL=0
    - COSIGN_YES=1 cosign sign --key hashivault://cosign-key --allow-insecure-registry --tlog-upload=false $HARBOR_URL/$HARBOR_PROJECT/auth-service:$CI_COMMIT_SHORT_SHA
  allow_failure: true
```

**`hashivault://cosign-key`** — schéma reconnu par Cosign
pour HashiCorp Vault. Juste le nom de la clé — pas le
chemin complet.

**`--tlog-upload=false`** — désactive Rekor transparency
log, pas nécessaire pour notre lab.

**`COSIGN_YES=1`** — répond automatiquement aux
confirmations interactives.

**`--allow-insecure-registry`** — Harbor tourne en HTTP,
Cosign refuse par défaut les registries sans HTTPS.

### Variables GitLab nécessaires

| Key | Description | Visibility |
|-----|-------------|------------|
| HARBOR_USERNAME | admin | Masked and hidden |
| HARBOR_PASSWORD | mdp Harbor | Masked and hidden |
| DTRACK_API_KEY | token OWASP DT | Masked and hidden |
| VAULT_SIGNING_TOKEN | token Vault cosign | Masked and hidden |

---

## 5. Problèmes rencontrés et solutions

### Problème 1 — OWASP DT 401 permission denied
**Cause** : token Automation sans permission PROJECT_CREATION.
**Solution** : Ajouter `PROJECT_CREATION_UPLOAD` aux
permissions du token dans Administration → Access Management.

### Problème 2 — Cosign schéma vault:// non reconnu
**Cause** : Cosign n'accepte pas `vault://` mais `hashivault://`.
**Solution** : Utiliser `hashivault://cosign-key`.

### Problème 3 — Vault 403 permission denied sur sha2-256
**Cause** : La politique n'autorisait que `transit/sign/cosign-key`
mais Cosign appelle `transit/sign/cosign-key/sha2-256`.
**Solution** : Ajouter `path "transit/sign/cosign-key/*"` avec
wildcard dans la politique Vault.

### Problème 4 — Variable VAULT_TOKEN non résolue
**Cause** : `VAULT_TOKEN` est une variable réservée par
Vault/Cosign — conflit avec la variable GitLab du même nom.
GitLab envoyait littéralement `$VAULT_TOKEN` au lieu
de la valeur.
**Solution** : Renommer la variable GitLab en
`VAULT_SIGNING_TOKEN` et l'assigner à `VAULT_TOKEN`
dans les variables du job.

```yaml
variables:
  VAULT_TOKEN: "$VAULT_SIGNING_TOKEN"
```

---

## 6. Le .gitlab-ci.yml complet — Phase 4

```yaml
stages:
  - test
  - build
  - scan
  - push
  - sign
  - sbom
  - dtrack

variables:
  HARBOR_URL: "192.168.157.20"
  HARBOR_PROJECT: "securebank"
  DOCKER_HOST: tcp://docker:2375
  DOCKER_TLS_CERTDIR: ""

# --- STAGE TEST ---
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

# --- STAGE BUILD ---
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

# --- STAGE SCAN ---
scan-auth:
  stage: scan
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
  script:
    - docker build -t $HARBOR_URL/$HARBOR_PROJECT/auth-service:$CI_COMMIT_SHORT_SHA app/auth-service/
    - docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --exit-code 0 --severity HIGH,CRITICAL $HARBOR_URL/$HARBOR_PROJECT/auth-service:$CI_COMMIT_SHORT_SHA
  allow_failure: true

scan-account:
  stage: scan
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
  script:
    - docker build -t $HARBOR_URL/$HARBOR_PROJECT/account-service:$CI_COMMIT_SHORT_SHA app/account-service/
    - docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --exit-code 0 --severity HIGH,CRITICAL $HARBOR_URL/$HARBOR_PROJECT/account-service:$CI_COMMIT_SHORT_SHA
  allow_failure: true

scan-transaction:
  stage: scan
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
  script:
    - docker build -t $HARBOR_URL/$HARBOR_PROJECT/transaction-service:$CI_COMMIT_SHORT_SHA app/transaction-service/
    - docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy:latest image --exit-code 0 --severity HIGH,CRITICAL $HARBOR_URL/$HARBOR_PROJECT/transaction-service:$CI_COMMIT_SHORT_SHA
  allow_failure: true

# --- STAGE PUSH ---
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

# --- STAGE SIGN ---
sign-auth:
  stage: sign
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
    VAULT_ADDR: "http://192.168.157.30:8200"
    VAULT_TOKEN: "$VAULT_SIGNING_TOKEN"
  script:
    - apk add --no-cache curl
    - curl -LO https://github.com/sigstore/cosign/releases/download/v2.2.0/cosign-linux-amd64
    - chmod +x cosign-linux-amd64
    - mv cosign-linux-amd64 /usr/local/bin/cosign
    - echo "$HARBOR_PASSWORD" | docker login $HARBOR_URL -u $HARBOR_USERNAME --password-stdin
    - export COSIGN_EXPERIMENTAL=0
    - COSIGN_YES=1 cosign sign --key hashivault://cosign-key --allow-insecure-registry --tlog-upload=false $HARBOR_URL/$HARBOR_PROJECT/auth-service:$CI_COMMIT_SHORT_SHA
  allow_failure: true

sign-account:
  stage: sign
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
    VAULT_ADDR: "http://192.168.157.30:8200"
    VAULT_TOKEN: "$VAULT_SIGNING_TOKEN"
  script:
    - apk add --no-cache curl
    - curl -LO https://github.com/sigstore/cosign/releases/download/v2.2.0/cosign-linux-amd64
    - chmod +x cosign-linux-amd64
    - mv cosign-linux-amd64 /usr/local/bin/cosign
    - echo "$HARBOR_PASSWORD" | docker login $HARBOR_URL -u $HARBOR_USERNAME --password-stdin
    - export COSIGN_EXPERIMENTAL=0
    - COSIGN_YES=1 cosign sign --key hashivault://cosign-key --allow-insecure-registry --tlog-upload=false $HARBOR_URL/$HARBOR_PROJECT/account-service:$CI_COMMIT_SHORT_SHA
  allow_failure: true

sign-transaction:
  stage: sign
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
    VAULT_ADDR: "http://192.168.157.30:8200"
    VAULT_TOKEN: "$VAULT_SIGNING_TOKEN"
  script:
    - apk add --no-cache curl
    - curl -LO https://github.com/sigstore/cosign/releases/download/v2.2.0/cosign-linux-amd64
    - chmod +x cosign-linux-amd64
    - mv cosign-linux-amd64 /usr/local/bin/cosign
    - echo "$HARBOR_PASSWORD" | docker login $HARBOR_URL -u $HARBOR_USERNAME --password-stdin
    - export COSIGN_EXPERIMENTAL=0
    - COSIGN_YES=1 cosign sign --key hashivault://cosign-key --allow-insecure-registry --tlog-upload=false $HARBOR_URL/$HARBOR_PROJECT/transaction-service:$CI_COMMIT_SHORT_SHA
  allow_failure: true

# --- STAGE SBOM ---
sbom-auth:
  stage: sbom
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
  script:
    - docker run --rm -v /var/run/docker.sock:/var/run/docker.sock anchore/syft:latest $HARBOR_URL/$HARBOR_PROJECT/auth-service:$CI_COMMIT_SHORT_SHA -o cyclonedx-json > auth-service-sbom.json
  artifacts:
    paths:
      - auth-service-sbom.json
    expire_in: 30 days
  allow_failure: true

sbom-account:
  stage: sbom
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
  script:
    - docker run --rm -v /var/run/docker.sock:/var/run/docker.sock anchore/syft:latest $HARBOR_URL/$HARBOR_PROJECT/account-service:$CI_COMMIT_SHORT_SHA -o cyclonedx-json > account-service-sbom.json
  artifacts:
    paths:
      - account-service-sbom.json
    expire_in: 30 days
  allow_failure: true

sbom-transaction:
  stage: sbom
  image: docker:27.0
  variables:
    DOCKER_HOST: "unix:///var/run/docker.sock"
  script:
    - docker run --rm -v /var/run/docker.sock:/var/run/docker.sock anchore/syft:latest $HARBOR_URL/$HARBOR_PROJECT/transaction-service:$CI_COMMIT_SHORT_SHA -o cyclonedx-json > transaction-service-sbom.json
  artifacts:
    paths:
      - transaction-service-sbom.json
    expire_in: 30 days
  allow_failure: true

# --- STAGE DTRACK ---
dtrack-auth:
  stage: dtrack
  image: python:3.11-slim
  script:
    - pip install requests
    - |
      python3 << EOF
      import requests, base64
      with open("auth-service-sbom.json", "r") as f:
          sbom_content = f.read()
      encoded = base64.b64encode(sbom_content.encode()).decode()
      payload = {
          "projectName": "auth-service",
          "projectVersion": "$CI_COMMIT_SHORT_SHA",
          "autoCreate": True,
          "bom": encoded
      }
      response = requests.put(
          "http://192.168.157.20:8080/api/v1/bom",
          headers={"X-Api-Key": "$DTRACK_API_KEY", "Content-Type": "application/json"},
          json=payload
      )
      print("Status:", response.status_code)
      EOF
  dependencies:
    - sbom-auth
  allow_failure: true

dtrack-account:
  stage: dtrack
  image: python:3.11-slim
  script:
    - pip install requests
    - |
      python3 << EOF
      import requests, base64
      with open("account-service-sbom.json", "r") as f:
          sbom_content = f.read()
      encoded = base64.b64encode(sbom_content.encode()).decode()
      payload = {
          "projectName": "account-service",
          "projectVersion": "$CI_COMMIT_SHORT_SHA",
          "autoCreate": True,
          "bom": encoded
      }
      response = requests.put(
          "http://192.168.157.20:8080/api/v1/bom",
          headers={"X-Api-Key": "$DTRACK_API_KEY", "Content-Type": "application/json"},
          json=payload
      )
      print("Status:", response.status_code)
      EOF
  dependencies:
    - sbom-account
  allow_failure: true

dtrack-transaction:
  stage: dtrack
  image: python:3.11-slim
  script:
    - pip install requests
    - |
      python3 << EOF
      import requests, base64
      with open("transaction-service-sbom.json", "r") as f:
          sbom_content = f.read()
      encoded = base64.b64encode(sbom_content.encode()).decode()
      payload = {
          "projectName": "transaction-service",
          "projectVersion": "$CI_COMMIT_SHORT_SHA",
          "autoCreate": True,
          "bom": encoded
      }
      response = requests.put(
          "http://192.168.157.20:8080/api/v1/bom",
          headers={"X-Api-Key": "$DTRACK_API_KEY", "Content-Type": "application/json"},
          json=payload
      )
      print("Status:", response.status_code)
      EOF
  dependencies:
    - sbom-transaction
  allow_failure: true
```

---

## Statut Phase 4
- [x] Trivy — scan vulnérabilités dans pipeline ✅
- [x] Syft — génération SBOM CycloneDX ✅
- [x] OWASP DT — 3 projets avec surveillance continue ✅
- [x] Cosign + Vault Transit — images signées ✅
- [x] Snapshot pipeline-phase4-complete ✅

## Prochaine étape — Phase 5
Déploiement AWS : EKS, ECR, KMS, IAM, IRSA.
