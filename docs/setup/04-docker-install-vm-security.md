# 04 — Installation Docker sur vm-security

## Objectif
Installation de Docker CE et Docker Compose sur vm-security.
Docker est indispensable car SonarQube, Harbor et OWASP
Dependency-Track vont tous tourner en containers Docker
sur cette VM.

## Environnement
- VM : vm-security (192.168.157.20)
- Docker version : 29.2.1
- Docker Compose version : v5.0.2

---

## Pourquoi Docker CE et pas docker.io ?

Il existe deux façons d'installer Docker sur Ubuntu :

**`docker.io`** — version maintenue par Ubuntu, légèrement
en retard sur les versions, dépréciée progressivement.

**Docker CE (Community Edition)** — version officielle
maintenue par Docker Inc, toujours à jour, avec
docker-compose-plugin intégré. C'est la méthode
recommandée en production et en entreprise.

On choisit Docker CE pour avoir docker-compose-plugin
(version moderne) au lieu de l'ancienne commande
docker-compose dépréciée.

---

## Installation

### 1. Installer les prérequis
```bash
sudo apt install -y ca-certificates curl
```

- ca-certificates — certificats SSL pour vérifier les connexions HTTPS
- curl — pour télécharger la clé GPG Docker

### 2. Créer le dossier pour les clés de confiance
```bash
sudo install -m 0755 -d /etc/apt/keyrings
```

`-m 0755` — permissions du dossier
`-d` — crée un dossier

C'est ici qu'on stocke les clés cryptographiques
des repos externes.

### 3. Télécharger la clé GPG officielle Docker
```bash
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  -o /etc/apt/keyrings/docker.asc
```

**Pourquoi une clé GPG ?**
C'est une clé cryptographique qui permet à Ubuntu de
vérifier que les paquets téléchargés viennent bien de
Docker Inc et n'ont pas été modifiés ou compromis.
C'est une mesure de sécurité essentielle pour les
repos externes.

### 4. Ajouter le repo officiel Docker
```bash
echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu noble stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list
```

Cette commande ajoute le repo Docker dans la liste
des sources apt d'Ubuntu.

- `echo` — génère le texte du repo
- `| tee` — écrit ce texte dans un fichier
- `docker.list` — fichier qui référence le repo Docker
- `signed-by` — indique la clé GPG à utiliser pour vérifier

### 5. Mettre à jour apt
```bash
sudo apt update
```

Maintenant apt connaît le repo Docker et ses paquets.

### 6. Installer Docker CE et ses composants
```bash
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
```

**Détail des composants :**

- `docker-ce` — Docker Community Edition, le moteur principal
- `docker-ce-cli` — interface ligne de commande Docker
- `containerd.io` — runtime de containers utilisé par Docker en interne
- `docker-compose-plugin` — Docker Compose version moderne
  intégrée à Docker (commande : `docker compose`)

---

## Logique de la procédure

C'est la procédure standard pour ajouter un repo
externe sécurisé sur Ubuntu :

1. Installer les outils nécessaires
2. Créer le dossier pour les clés
3. Télécharger la clé de confiance GPG
4. Ajouter le repo
5. Mettre à jour apt
6. Installer

Cette même logique s'applique à tous les outils
installés via repo externe (GitLab Runner, Docker, etc.)

---

## Configuration post-installation

### Démarrer Docker et activer au démarrage
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

- `start` — démarre Docker maintenant
- `enable` — démarre Docker automatiquement à chaque reboot

### Ajouter l'utilisateur au groupe docker
```bash
sudo usermod -aG docker hicham
```

Permet d'utiliser Docker sans sudo.
⚠️ Se déconnecter et reconnecter pour que le groupe
soit pris en compte.

### Vérifier l'installation
```bash
docker --version
docker compose version
docker run hello-world
```

Résultats attendus :
- Docker version 29.2.1 ✅
- Docker Compose version v5.0.2 ✅
- Hello from Docker! ✅

---

## Différence docker compose vs docker-compose

| Commande | Version | Statut |
|----------|---------|--------|
| `docker-compose` | v1.x — Python | Déprécié |
| `docker compose` | v2.x — Go | Actuel ✅ |

On utilise toujours `docker compose` (sans tiret).

---

## Statut
- [x] Docker CE installé ✅
- [x] Docker Compose plugin installé ✅
- [x] Docker démarré et enabled ✅
- [x] Utilisateur ajouté au groupe docker ✅
- [x] Snapshot docker-ready ✅
