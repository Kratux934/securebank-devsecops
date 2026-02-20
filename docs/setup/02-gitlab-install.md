# 02 — Installation GitLab CE

## Objectif
Installation et configuration de GitLab Community Edition
sur vm-gitlab — c'est le cœur du pipeline CI/CD du projet.

## Environnement
- VM : vm-gitlab (192.168.157.10)
- GitLab version : v18.9.0 CE
- Installation : bare metal (pas Docker)

## Pourquoi bare metal et pas Docker
GitLab est un outil très lourd qui contient en interne
Nginx, PostgreSQL, Redis, Sidekiq, Puma. En bare metal
tout est géré automatiquement et de façon optimisée.
C'est la méthode officielle recommandée par GitLab pour
la production et celle utilisée en entreprise.

## Installation

### 1. Prérequis
```bash
sudo apt install -y curl openssh-server ca-certificates tzdata perl
```

**Détail des prérequis :**
- curl — télécharger le script d'installation GitLab
- openssh-server — connexions SSH des développeurs
- ca-certificates — vérification des certificats HTTPS
- tzdata — gestion des fuseaux horaires pour les logs
- perl — scripts internes GitLab

### 2. Ajout du dépôt officiel GitLab
```bash
curl -sS https://packages.gitlab.com/install/repositories/gitlab/gitlab-ce/script.deb.sh | sudo bash
```

Ce script configure le dépôt officiel GitLab dans apt.

### 3. Installation
```bash
sudo EXTERNAL_URL="http://192.168.157.10" apt install -y gitlab-ce
```

**EXTERNAL_URL** — URL à laquelle GitLab est accessible.
Utilisée pour générer les liens, URLs de clone, webhooks
et emails de notification.

### 4. Récupération du mot de passe root initial
```bash
sudo cat /etc/gitlab/initial_root_password
```

⚠️ Ce fichier est supprimé automatiquement après 24h.
Sauvegarder le mot de passe dans KeePass immédiatement.

## Sécurisation post-installation

### Changer le mot de passe root
Icône profil → Modifier le profil → Mot de passe

### Désactiver les inscriptions publiques
Zone d'administration → Paramètres → Général →
Restrictions de visibilité → décocher Inscriptions activées

## Vérification
- Interface accessible : http://192.168.157.10 ✅
- Version : v18.9.0 CE ✅
- Connexion admin : ✅
- Inscriptions publiques désactivées : ✅
- Projet securebank créé : ✅

## Statut
- [x] GitLab CE installé ✅
- [x] Sécurisation post-install ✅
- [x] Projet securebank créé ✅
