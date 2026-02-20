# 03 — Installation GitLab Runner

## Objectif
Installation et enregistrement du GitLab Runner sur vm-gitlab.
Le Runner est le composant qui exécute concrètement les jobs
du pipeline CI/CD.

## Concept clé
GitLab = le chef qui définit les pipelines
GitLab Runner = l'ouvrier qui exécute les jobs

Sans Runner, le pipeline est défini mais jamais exécuté.

## Environnement
- VM : vm-gitlab (192.168.157.10)
- GitLab Runner version : 18.9.0
- Executor : Docker
- Docker version : 28.2.2

---

## Problème rencontré — Conflit de dépendances apt

### Erreur
```
gitlab-runner : Dépend: gitlab-runner-helper-images (= 18.8.0-1)
mais 18.9.0-1 devra être installé
```

### Cause
GitLab CE installé en version 18.9.0 mais le paquet
gitlab-runner disponible via apt était en 18.8.0 avec
une dépendance incompatible sur gitlab-runner-helper-images.
Décalage classique entre versions de paquets dans les repos.

### Solution — Installation via binaire officiel
On contourne apt en téléchargeant directement le binaire
depuis le serveur officiel GitLab. Plus fiable pour les
outils qui évoluent rapidement.

---

## Installation du Runner

### 1. Téléchargement du binaire officiel
```bash
sudo curl -L --output /usr/local/bin/gitlab-runner \
  https://gitlab-runner-downloads.s3.amazonaws.com/latest/binaries/gitlab-runner-linux-amd64
```

### 2. Rendre le binaire exécutable
```bash
sudo chmod +x /usr/local/bin/gitlab-runner
```

**Pourquoi chmod +x ?** Par défaut un fichier téléchargé
n'est pas exécutable sur Linux. Cette commande lui donne
le droit d'être exécuté comme un programme.

### 3. Créer l'utilisateur système dédié
```bash
sudo useradd --comment 'GitLab Runner' \
  --create-home gitlab-runner --shell /bin/bash
```

**Pourquoi un utilisateur dédié ?** Bonne pratique de
sécurité — le Runner tourne avec son propre utilisateur
aux permissions limitées, pas avec root.

### 4. Installer comme service système
```bash
sudo gitlab-runner install \
  --user=gitlab-runner \
  --working-directory=/home/gitlab-runner
```

### 5. Démarrer le service
```bash
sudo gitlab-runner start
```

### 6. Vérifier que le service tourne
```bash
sudo gitlab-runner status
```
Résultat attendu : `gitlab-runner: Service is running`

---

## Installation Docker

Le Runner utilise Docker pour exécuter les jobs dans des
containers isolés. Chaque job démarre dans un environnement
propre — bonne pratique enterprise.

```bash
sudo apt install -y docker.io
```

### Ajouter les utilisateurs au groupe docker
```bash
sudo usermod -aG docker gitlab-runner
sudo usermod -aG docker hicham
```

**Pourquoi ?** Sans ça Docker nécessite sudo pour chaque
commande. En ajoutant les utilisateurs au groupe docker
ils peuvent utiliser Docker directement.

⚠️ Se déconnecter et reconnecter de PuTTY après cette
commande pour que le groupe soit pris en compte.

### Redémarrer le Runner
```bash
sudo gitlab-runner restart
```

### Vérifier Docker
```bash
docker run hello-world
```
Résultat attendu : `Hello from Docker!`

---

## Créer l'Instance Runner sur GitLab

Avant d'enregistrer le Runner depuis la VM, il faut
d'abord le créer dans l'interface GitLab.

**Chemin exact :**
1. Connecte toi sur http://192.168.157.10
2. Clique sur l'icône Admin (clé à molette) en haut à gauche
3. Dans le menu gauche → CI/CD → Runners
4. Clique sur le bouton **New instance runner**
5. Remplis :
   - Tags : docker, linux, securebank
   - Coche : Run untagged jobs ✅
   - Description : securebank-runner
6. Clique **Create runner**
7. GitLab affiche la commande d'enregistrement avec le token
8. ⚠️ Copie ce token dans KeePass immédiatement —
   il ne sera plus affiché après cette page

**Instance Runner vs Project Runner :**
- Instance Runner → disponible pour tous les projets ✅
- Project Runner → limité à un seul projet
On choisit Instance Runner pour notre lab.

---

## Enregistrement du Runner sur GitLab

### Commande d'enregistrement
```bash
sudo gitlab-runner register \
  --url http://192.168.157.10 \
  --token <token_copié_depuis_gitlab>
```

Répondre aux questions :
- GitLab instance URL : http://192.168.157.10
- Name : securebank-runner
- Executor : docker
- Default image : docker:24.0

**Pourquoi executor docker ?** Chaque job tourne dans
un container isolé et propre. Pas de pollution entre
les jobs. Standard en entreprise.

---

## Vérification finale

Retourner sur GitLab → Admin → CI/CD → Runners
Le runner doit apparaître avec le statut **Online** (point vert)

- Runner status : service is running ✅
- Docker hello-world : Hello from Docker! ✅
- Runner online sur GitLab : 1 Online ✅

---

## Statut
- [x] GitLab Runner installé via binaire ✅
- [x] Docker installé et configuré ✅
- [x] Runner enregistré sur GitLab ✅
- [x] Runner online ✅
- [x] Snapshot gitlab-runner-docker-ready ✅
