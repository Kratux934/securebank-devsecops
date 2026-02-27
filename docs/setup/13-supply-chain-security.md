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

Trivy et Syft sont utilisés via `docker run --rm` —
ils tournent dans des containers éphémères détruits
après exécution. Rien n'est installé sur vm-gitlab.

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

**`-v /var/run/docker.sock:/var/run/docker.sock`** — monte
le socket Docker pour que Trivy puisse accéder aux images
locales.

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

**Target** — l'élément précis scanné. Soit l'OS entier,
soit un package Python avec son fichier METADATA.

**Type** — catégorie : `debian` pour l'OS, `python-pkg`
pour les packages pip installés via pip.

**Vulnerabilities** — nombre de CVE trouvées.
`0` = propre, `2` = 2 vulnérabilités.

**Secrets** — Trivy cherche aussi les secrets hardcodés
(clés API, mots de passe). `-` = pas scanné.

C'est l'inventaire complet de tous les composants de
l'image avec leur statut de sécurité.

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
La règle : est-ce que MON CODE utilise la fonctionnalité
vulnérable ?
Exemple : CVE sur upload de fichiers multipart alors
que notre service ne fait que du JSON → faux positif.

**Vrai positif** — la vulnérabilité est réelle et
notre code utilise la fonctionnalité vulnérable.
Exemple : python-jose CRITICAL — on utilise JWT → vrai positif.

**Risque accepté** — vulnérabilité réelle mais acceptée
consciemment avec justification documentée.
Exemple : libc-bin — pas de fix disponible, composant OS.

Le processus en entreprise :
```
Trivy détecte une vulnérabilité
        ↓
Analyste examine :
├── La fonctionnalité est-elle utilisée ?
├── Le service est-il exposé ?
└── Y a-t-il un fix disponible ?
        ↓
Décision :
├── Vrai positif  → ouvrir un ticket de correction
├── Faux positif  → documenter et ignorer
└── Risque accepté → noter dans le registre des risques
```

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
de surveiller en continu — dès qu'une nouvelle CVE
apparaît sur un de tes packages, tu reçois une alerte.

### Format CycloneDX
Standard industrie reconnu par OWASP DT, GitHub,
AWS Inspector. Format JSON avec tous les composants
et leurs métadonnées.

```json
{
  "bomFormat": "CycloneDX",
  "specVersion": "1.6",
  "serialNumber": "urn:uuid:7c970fad-...",
  "components": [
    {
      "name": "fastapi",
      "version": "0.115.0",
      "type": "library"
    }
  ]
}
```

Notre SBOM contient **2934 composants** — packages OS,
librairies Python, binaires système.

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
Téléchargeable depuis l'interface GitLab → job → Artifacts.

**`cyclonedx-json`** — format standard reconnu par OWASP DT.

**`anchore/syft:latest`** — Syft tourne dans un container
éphémère. Rien n'est installé sur vm-gitlab.

**Passage des artifacts entre jobs** — le fichier SBOM
généré par Syft est récupéré par le job dtrack grâce
à `dependencies`. Sans ça chaque job est isolé et ne
voit pas les fichiers des autres jobs.

---

## 3. OWASP Dependency-Track

### C'est quoi OWASP DT ?
Reçoit les SBOMs et surveille en continu. Dès qu'une
nouvelle CVE apparaît sur un package de tes images,
tu reçois une alerte automatique — sans relancer le pipeline.

### Différence avec Trivy
```
Trivy    → meilleur détection CVE Python pip (temps réel)
OWASP DT → meilleur surveillance continue OS + alertes auto
```
Les deux sont complémentaires — Trivy détecte au build,
OWASP DT surveille en permanence après le déploiement.

### Récupérer le token API

OWASP DT → **Administration** → **Access Management**
→ **Teams** → **Automation** → copier le token API.

### Configuration des permissions du token

**Administration** → **Access Management** → **Teams**
→ **Automation** → **Permissions** → ajouter :

- `PROJECT_CREATION_UPLOAD` ✅ — crée le projet + upload BOM
- `BOM_UPLOAD` ✅ — upload du SBOM
- `VIEW_PORTFOLIO` ✅ — voir les projets
- `VIEW_VULNERABILITY` ✅ — voir les vulnérabilités

### Ajouter le token dans GitLab

GitLab → projet → **Settings** → **CI/CD** → **Variables** :
- Key : `DTRACK_API_KEY`
- Value : ton token OWASP DT
- Visibility : **Masked and hidden** ✅

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

**`dependencies: sbom-auth`** — GitLab télécharge
automatiquement l'artifact SBOM du job sbom-auth dans
le workspace de ce job. C'est le seul moyen de partager
des fichiers entre jobs car chaque job tourne dans un
container isolé.

**`autoCreate: True`** — crée le projet dans OWASP DT
automatiquement s'il n'existe pas. On a 3 projets séparés :
auth-service, account-service, transaction-service.

**`base64`** — OWASP DT attend le SBOM encodé en base64.

**`projectVersion: $CI_COMMIT_SHORT_SHA`** — chaque push
crée une nouvelle version dans OWASP DT. Tu peux comparer
les vulnérabilités entre versions.

### Onglets OWASP DT et leur utilité en entreprise

**Audit Vulnerabilities** — onglet principal. Triage des CVE :
vrai positif → ticket de correction,
faux positif → documenter et supprimer avec justification,
risque accepté → noter avec date de révision.
Filtrer par statut `New` pour voir uniquement les nouvelles.

**Exploit Prediction** — priorise les CVE selon la
probabilité d'exploitation active. Une CVE Medium avec
exploit actif est plus urgente qu'une Critical sans exploit.

**Policy Violation** — règles automatiques configurables :
"aucune CVE Critical non corrigée depuis 30 jours".

**Dependency Graph** — visualise les dépendances transitives.

**Notifications** — à configurer en Phase 8 :
email/Slack quand nouvelle CVE Critical détectée.

---

## 4. Cosign + Vault Transit — Signature des images

### Pourquoi signer les images ?

Sans signature :
```
Pipeline build image → push sur Harbor
Quelqu'un modifie l'image sur Harbor
Kubernetes déploie l'image modifiée ← personne ne le sait ⚠️
```

Avec signature :
```
Pipeline signe l'image → signature stockée sur Harbor
Kubernetes vérifie la signature avant déploiement
Image modifiée → signature invalide → déploiement refusé ✅
```

### Cosign seul vs Cosign + Vault

**Sans Vault — clé locale** :
```bash
cosign generate-key-pair  # génère cosign.key + cosign.pub
cosign sign --key cosign.key image:tag
```
Cosign signe directement avec sa propre clé privée.
La clé `cosign.key` est un fichier — peut être volée.

**Avec Vault Transit — méthode enterprise (notre choix)** :
```bash
cosign sign --key hashivault://cosign-key image:tag
```
Vault garde la clé privée. Cosign demande à Vault de
signer — la clé ne quitte jamais Vault.

### Le flux de signature complet

```
1. Image pushée sur Harbor
        ↓
2. Cosign calcule le hash de l'image
   sha256:abc123... ← empreinte unique
   (Cosign calcule le hash, pas Vault)
        ↓
3. Cosign envoie le hash à Vault Transit :
   "Signe moi sha256:abc123..."
   (authentification avec VAULT_TOKEN)
        ↓
4. Vault signe le hash avec sa clé privée ECDSA-P256
   et retourne uniquement la signature
   La clé privée ne sort jamais de Vault ✅
        ↓
5. Cosign push la signature sur Harbor
   liée à l'image
        ↓
6. (Phase 6) Kyverno lit cosign.pub depuis le repo
   et vérifie la signature avant tout déploiement
```

### La clé publique dans le repo

La clé publique `cosign.pub` est dans le repo car :
- Kyverno en a besoin en Phase 6 pour vérifier les signatures
- Elle est versionnée — historique des changements de clé
- Elle n'est pas secrète — la partager est normal et recommandé

```
Clé privée  → reste dans Vault, signe ← ne sort JAMAIS
Clé publique → dans cosign.pub, vérifie ← visible par tous
```

Ce qui est signé avec la clé privée ne peut être vérifié
qu'avec la clé publique correspondante — cryptographie
asymétrique. Pour l'instant personne ne vérifie encore
les signatures — la vérification sera ajoutée en Phase 6
avec Kyverno.

### Configuration Vault Transit — étape par étape

**1. Se connecter à vm-vault**
```bash
export VAULT_ADDR='http://192.168.157.30:8200'
vault operator unseal  # x3 avec les unseal keys KeePass
vault login            # avec le root token
```

**2. Activer le moteur Transit**
```bash
vault secrets enable transit
```
Transit = moteur cryptographique de Vault spécialisé
dans la signature et le chiffrement sans exposer les clés.
Différent du moteur KV utilisé pour les secrets — Transit
ne stocke pas de données, il fait des opérations crypto.

**3. Créer la clé de signature**
```bash
vault write -f transit/keys/cosign-key type=ecdsa-p256
```
`ecdsa-p256` — algorithme de signature utilisé par Cosign.
`exportable: false` — la clé privée ne peut jamais être
exportée hors de Vault ✅
`supports_signing: true` — la clé peut signer ✅

**4. Créer la politique Vault**
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

`transit/sign/cosign-key/*` — le wildcard `*` est
OBLIGATOIRE. Cosign appelle le chemin avec un suffixe
`/sha2-256` — sans le wildcard Vault refuse avec 403.

La politique applique le **principe du moindre privilège** :
le pipeline ne peut que signer, pas lire les secrets
ni gérer Vault. En entreprise les policies sont versionnées
dans Git et appliquées via Terraform.

**5. Créer le token Vault**
```bash
vault token create -policy=cosign-policy -ttl=720h
```
Copie le token affiché — il sera stocké dans GitLab.
`-ttl=720h` = 30 jours. En production on utiliserait
AppRole avec renouvellement automatique.

**6. Exporter la clé publique**
```bash
vault read transit/keys/cosign-key
```
Copier le bloc `public_key` depuis le champ `keys` :
```
-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE/4D0IDTSrwABPRj8UD2jfHIjFTLF
ndzCMacjK3tGM9MbnGiis06tmpD9tco8Xi6uv5udq0T6ukEdGiVYsxurMA==
-----END PUBLIC KEY-----
```

**7. Créer cosign.pub dans le repo GitLab**
GitLab → projet → **Add file** → **Create new file**
Nom : `cosign.pub`
Contenu : coller la clé publique → commiter.

**8. Ajouter la variable dans GitLab**

GitLab → Settings → CI/CD → Variables :

| Key | Value | Visibility |
|-----|-------|------------|
| `VAULT_SIGNING_TOKEN` | token créé à l'étape 5 | Masked and hidden |

⚠️ **IMPORTANT — ne pas nommer `VAULT_TOKEN`** !
`VAULT_TOKEN` est une variable réservée par Vault/Cosign.
GitLab enverrait littéralement le texte `$VAULT_TOKEN`
au lieu de la valeur — Vault retournerait 403.
Nommer `VAULT_SIGNING_TOKEN` et l'assigner dans le job :
```yaml
variables:
  VAULT_TOKEN: "$VAULT_SIGNING_TOKEN"
```

### Job Cosign dans .gitlab-ci.yml — expliqué ligne par ligne

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

**`VAULT_ADDR`** — adresse de Vault sur vm-vault.
Cosign en a besoin pour savoir où envoyer les requêtes.

**`VAULT_TOKEN: "$VAULT_SIGNING_TOKEN"`** — assigne le token
depuis la variable GitLab renommée vers la variable
réservée que Cosign/Vault utilisent.

**`apk add --no-cache curl`** — installe curl dans l'image
Alpine. Nécessaire pour télécharger Cosign.

**`curl -LO .../cosign-linux-amd64`** — télécharge le binaire
Cosign depuis GitHub. Cosign n'est pas dans les packages
Alpine donc on le télécharge manuellement.

**`chmod +x && mv .../cosign`** — rend Cosign exécutable
et le place dans le PATH pour pouvoir l'appeler directement.

**`docker login`** — s'authentifie à Harbor. Cosign utilise
les credentials Docker pour accéder à l'image et pousser
la signature sur Harbor.

**`COSIGN_EXPERIMENTAL=0`** — désactive le mode expérimental
qui nécessiterait Rekor (transparency log public) —
pas utile dans notre lab.

**`COSIGN_YES=1`** — répond automatiquement `yes` aux
confirmations interactives. Sans ça le pipeline se bloque
en attendant une saisie manuelle.

**`--key hashivault://cosign-key`** — dit à Cosign d'utiliser
Vault Transit. `hashivault://` est le schéma reconnu par
Cosign pour HashiCorp Vault. Juste le nom de la clé —
pas le chemin complet `transit/keys/cosign-key`.

**`--allow-insecure-registry`** — Harbor tourne en HTTP
dans notre lab. Cosign refuse par défaut les registries
sans HTTPS — ce flag l'autorise.

**`--tlog-upload=false`** — désactive l'upload vers Rekor,
le transparency log public de Sigstore. Pas nécessaire
pour notre lab privé.

---

## 5. Variables GitLab — récapitulatif complet

| Key | Description | Visibility |
|-----|-------------|------------|
| HARBOR_USERNAME | `admin` | Masked and hidden |
| HARBOR_PASSWORD | mot de passe Harbor | Masked and hidden |
| DTRACK_API_KEY | token OWASP DT Automation | Masked and hidden |
| VAULT_SIGNING_TOKEN | token Vault cosign-policy | Masked and hidden |

---

## 6. Problèmes rencontrés et solutions

### Problème 1 — OWASP DT 401 permission denied
**Erreur** : `Status: 401 — permission denied`
**Cause** : token Automation sans permission PROJECT_CREATION.
**Solution** : Ajouter `PROJECT_CREATION_UPLOAD` aux
permissions dans Administration → Access Management.

### Problème 2 — Cosign schéma vault:// non reconnu
**Erreur** : `unrecognized scheme: vault://`
**Cause** : Cosign n'accepte pas `vault://`.
**Solution** : Utiliser `hashivault://cosign-key`.

### Problème 3 — Vault 403 sur sha2-256
**Erreur** : `403 permission denied` sur `/transit/sign/cosign-key/sha2-256`
**Cause** : La politique autorisait `transit/sign/cosign-key`
mais Cosign appelle `transit/sign/cosign-key/sha2-256`.
**Solution** : Ajouter le wildcard dans la politique :
```hcl
path "transit/sign/cosign-key/*" {
  capabilities = ["update"]
}
```

### Problème 4 — Variable VAULT_TOKEN non résolue
**Erreur** : `403 invalid token` — Vault reçoit `$VAULT_TOKEN`
au lieu de la valeur du token.
**Cause** : `VAULT_TOKEN` est une variable réservée.
Conflit avec la variable GitLab du même nom.
**Solution** : Renommer la variable GitLab en
`VAULT_SIGNING_TOKEN` et l'assigner dans le job :
```yaml
variables:
  VAULT_TOKEN: "$VAULT_SIGNING_TOKEN"
```

### Problème 5 — Harbor 443 connection refused
**Erreur** : `dial tcp 192.168.157.20:443: connect: connection refused`
**Cause** : Docker essaie de se connecter à Harbor en HTTPS.
**Solution** : Ajouter Harbor comme insecure registry
sur vm-gitlab :
```bash
echo '{"insecure-registries":["192.168.157.20"]}' | sudo tee /etc/docker/daemon.json
sudo systemctl stop docker.socket && sudo systemctl stop docker
sudo systemctl start docker
docker info | grep -A5 "Insecure"  # vérifier
```
⚠️ Le JSON doit être valide — vérifier la présence du `}` final.
Si Docker ne prend pas en compte la config, vérifier le JSON :
`sudo cat /etc/docker/daemon.json`

---

## 7. Le .gitlab-ci.yml complet — Phase 4

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
- [x] Syft — génération SBOM CycloneDX (2934 composants) ✅
- [x] OWASP DT — 3 projets avec surveillance continue ✅
- [x] Cosign + Vault Transit — images signées ✅
- [x] cosign.pub — clé publique dans le repo ✅
- [x] Snapshot pipeline-phase4-complete ✅

## Prochaine étape — Phase 5
Déploiement AWS : EKS, ECR, KMS, IAM, IRSA.
Cosign sera reconfiguré avec AWS KMS en Phase 5.
Kyverno vérifiera les signatures en Phase 6.
