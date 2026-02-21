# 07 — Installation OWASP Dependency-Track

## Objectif
Installation et configuration d'OWASP Dependency-Track
sur vm-security. C'est l'outil SCA du projet — il analyse
les dépendances de l'application pour détecter les CVE
et les suit dans le temps.

## Concept clé — SCA et SBOM
SCA = Software Composition Analysis.

OWASP DT reçoit les **SBOM** (Software Bill of Materials)
générés par Syft dans le pipeline et analyse chaque
composant contre les bases de données de CVE connues.

**Différence avec Trivy :**
- Trivy — scan ponctuel à chaque pipeline
- OWASP DT — suivi continu dans le temps avec dashboard,
  historique des vulnérabilités et alertes

En fintech c'est indispensable pour la conformité —
on peut prouver à tout moment l'état de sécurité
de toutes les dépendances.

## Environnement
- VM : vm-security (192.168.157.20)
- OWASP DT version : latest
- Port frontend : 8081
- Port API : 8080
- Installation : Docker Compose

---

## Installation via Docker Compose

### 1. Créer le dossier de travail
```bash
mkdir -p ~/owasp-dt && cd ~/owasp-dt
```

### 2. Créer le fichier docker-compose.yml
```bash
nano docker-compose.yml
```

Contenu :
```yaml
services:
  dtrack-apiserver:
    image: dependencytrack/apiserver
    container_name: dtrack-apiserver
    restart: unless-stopped
    environment:
      - ALPINE_DATABASE_MODE=external
      - ALPINE_DATABASE_URL=jdbc:postgresql://dtrack-db:5432/dtrack
      - ALPINE_DATABASE_DRIVER=org.postgresql.Driver
      - ALPINE_DATABASE_USERNAME=dtrack
      - ALPINE_DATABASE_PASSWORD=dtrack
    volumes:
      - dtrack-data:/data
    ports:
      - "8080:8080"
    depends_on:
      - dtrack-db

  dtrack-frontend:
    image: dependencytrack/frontend
    container_name: dtrack-frontend
    restart: unless-stopped
    environment:
      - API_BASE_URL=http://192.168.157.20:8080
    ports:
      - "8081:8080"
    depends_on:
      - dtrack-apiserver

  dtrack-db:
    image: postgres:15
    container_name: dtrack-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: dtrack
      POSTGRES_PASSWORD: dtrack
      POSTGRES_DB: dtrack
    volumes:
      - dtrack-db-data:/var/lib/postgresql/data

volumes:
  dtrack-data:
  dtrack-db-data:
```

**Détail des composants :**

`dtrack-apiserver` — backend OWASP DT, reçoit les SBOMs,
analyse les CVE, expose l'API sur le port 8080.

`dtrack-frontend` — interface web sur le port 8081.
Architecture frontend/backend séparée.

`dtrack-db` — PostgreSQL pour stocker les projets,
composants et vulnérabilités dans le temps.

`API_BASE_URL` — indique au frontend où trouver le backend.
On met l'IP fixe de vm-security.

### 3. Lancer OWASP DT
```bash
docker compose up -d
```

⚠️ OWASP DT prend 2-3 minutes à démarrer complètement
la première fois. Page blanche = attendre et rafraîchir.

---

## Configuration post-installation

### Accès initial
URL frontend : http://192.168.157.20:8081
Login : admin
Mot de passe : admin (à changer immédiatement)

⚠️ Sauvegarder le nouveau mot de passe dans KeePass.

### Créer le projet SecureBank

**Chemin exact :**
Projects → Create Project

Paramètres :
- Name : securebank
- Version : 1.0.0
- Classifier : Application

---

## Ce que fera OWASP DT dans le pipeline

1. Syft génère un SBOM (liste de toutes les dépendances)
2. Le pipeline envoie le SBOM à l'API OWASP DT
3. OWASP DT analyse chaque composant contre NVD, OSV,
   GitHub Advisory et autres bases de CVE
4. Le dashboard affiche les vulnérabilités par sévérité
5. Des alertes sont déclenchées sur les CVE critiques

---

## Ports utilisés sur vm-security

| Service | Port | URL |
|---------|------|-----|
| SonarQube | 9000 | http://192.168.157.20:9000 |
| Harbor | 80 | http://192.168.157.20 |
| OWASP DT API | 8080 | http://192.168.157.20:8080 |
| OWASP DT UI | 8081 | http://192.168.157.20:8081 |

---

## Vérification finale
- OWASP DT accessible : http://192.168.157.20:8081 ✅
- Connexion admin : ✅
- Projet securebank créé : ✅

---

## Statut
- [x] OWASP Dependency-Track installé ✅
- [x] Projet securebank créé ✅
- [x] Snapshot owasp-dt-ready ✅
