# 05 — Installation SonarQube

## Objectif
Installation et configuration de SonarQube Community Edition
sur vm-security via Docker Compose. SonarQube est l'outil
SAST du projet — il analyse le code source statiquement
pour détecter les failles de sécurité avant même que
le code soit exécuté.

## Concept clé — SAST
SAST = Static Application Security Testing.
SonarQube analyse le code **sans l'exécuter** pour trouver :
- Injections SQL
- Mauvaise gestion des tokens JWT
- Mots de passe hardcodés
- Failles OWASP Top 10
- Code mort, bugs, mauvaises pratiques

Dans notre pipeline il est au **Stage 1** — si SonarQube
trouve un problème critique, le pipeline s'arrête
immédiatement. Le code ne part jamais en prod.

## Environnement
- VM : vm-security (192.168.157.20)
- SonarQube version : Community Edition (latest)
- Base de données : PostgreSQL 15
- Port : 9000
- Installation : Docker Compose

---

## Prérequis système

SonarQube est gourmand en ressources kernel. Ces paramètres
doivent être augmentés sinon SonarQube refuse de démarrer.

### Appliquer immédiatement
```bash
sudo sysctl -w vm.max_map_count=524288
sudo sysctl -w fs.file-max=131072
```

### Rendre permanent au reboot
```bash
echo "vm.max_map_count=524288" | sudo tee -a /etc/sysctl.conf
echo "fs.file-max=131072" | sudo tee -a /etc/sysctl.conf
```

**Pourquoi `/etc/sysctl.conf` ?**
C'est le fichier de configuration permanente du kernel Linux.
Tout ce qui y est écrit est chargé automatiquement à chaque
démarrage de la VM.

**`tee -a`** — écrit en mode append (ajout à la fin) sans
écraser le contenu existant du fichier.

---

## Installation via Docker Compose

### 1. Créer le dossier de travail
```bash
mkdir -p ~/sonarqube && cd ~/sonarqube
```

`mkdir -p` — crée le dossier et les parents si nécessaire.
Sans `-p` une erreur est levée si le dossier existe déjà.

### 2. Créer le fichier docker-compose.yml
```bash
nano docker-compose.yml
```

Contenu :
```yaml
services:
  sonarqube:
    image: sonarqube:community
    container_name: sonarqube
    restart: unless-stopped
    depends_on:
      - sonarqube-db
    environment:
      SONAR_JDBC_URL: jdbc:postgresql://sonarqube-db:5432/sonar
      SONAR_JDBC_USERNAME: sonar
      SONAR_JDBC_PASSWORD: sonar
    volumes:
      - sonarqube_data:/opt/sonarqube/data
      - sonarqube_logs:/opt/sonarqube/logs
      - sonarqube_extensions:/opt/sonarqube/extensions
    ports:
      - "9000:9000"

  sonarqube-db:
    image: postgres:15
    container_name: sonarqube-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: sonar
      POSTGRES_PASSWORD: sonar
      POSTGRES_DB: sonar
    volumes:
      - sonarqube_db:/var/lib/postgresql/data

volumes:
  sonarqube_data:
  sonarqube_logs:
  sonarqube_extensions:
  sonarqube_db:
```

**Détail des composants :**

`sonarqube` — container principal, interface web port 9000.

`sonarqube-db` — PostgreSQL, base de données de SonarQube.
Stocke les analyses, configurations, utilisateurs.

`depends_on` — SonarQube démarre seulement après PostgreSQL.

`restart: unless-stopped` — redémarrage automatique après
reboot VM, sauf si arrêt manuel.

`volumes` — persistance des données. Sans volumes toutes
les analyses sont perdues à chaque recréation des containers.

### 3. Lancer SonarQube
```bash
docker compose up -d
```

`up` — démarre tous les containers du fichier compose.
`-d` — mode detached, tourne en arrière-plan.

### 4. Vérifier que les containers tournent
```bash
docker compose ps
```

Résultat attendu :
- sonarqube → Up, port 9000 ✅
- sonarqube-db → Up, port 5432 ✅

---

## Configuration post-installation

### Accès initial
URL : http://192.168.157.20:9000
Login : admin
Mot de passe : admin (à changer immédiatement)

⚠️ Sauvegarder le nouveau mot de passe dans KeePass.

---

## Configuration du Quality Gate SecureBank-QG

### Pourquoi un Quality Gate custom ?
Le Quality Gate par défaut "Sonar way" est générique.
On crée un Quality Gate adapté aux contraintes d'une
fintech — plus strict sur la sécurité.

### Chemin exact
Quality Gates → Create → Nom : SecureBank-QG

### Conditions configurées

| Métrique | Opérateur | Valeur | Raison |
|----------|-----------|--------|--------|
| Issues | is greater than | 0 | Zéro tolérance sur les problèmes |
| Security Hotspots Reviewed | is less than | 100% | Tous les points chauds revus |
| Coverage | is less than | 70% | Couverture de tests minimum |
| Duplicated Lines | is greater than | 3% | Limite la duplication de code |

### Définir comme Quality Gate par défaut
3 points `...` en haut à droite → **Set as Default**

Tous les projets créés sur SonarQube utiliseront
automatiquement SecureBank-QG.

---

## Vérification finale
- SonarQube accessible : http://192.168.157.20:9000 ✅
- Connexion admin : ✅
- Quality Gate SecureBank-QG créé : ✅
- SecureBank-QG défini comme défaut : ✅

---

## Statut
- [x] SonarQube installé via Docker Compose ✅
- [x] PostgreSQL configuré ✅
- [x] Quality Gate SecureBank-QG configuré ✅
- [x] Snapshot docker-ready ✅
