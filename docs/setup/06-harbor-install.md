# 06 — Installation Harbor

## Objectif
Installation et configuration de Harbor sur vm-security.
Harbor est le registry de containers privé local du projet.
Il stocke et gère les images Docker pour les environnements
de dev et test.

## Concept clé — Registry privé
Un registry c'est l'endroit où on stocke les images Docker.

- **Docker Hub** — registry public, tout le monde peut voir
- **Harbor** — registry privé local avec sécurité avancée
- **AWS ECR** — registry privé cloud (prod)

Harbor ajoute par rapport à un simple registry :
- Scan de vulnérabilités automatique sur les images
- Contrôle d'accès par projet et utilisateur
- Signature des images
- Politiques de rétention

Dans notre pipeline Harbor = registry local dev/test.
AWS ECR = registry production.

## Environnement
- VM : vm-security (192.168.157.20)
- Harbor version : v2.10.0
- Port : 80 (HTTP)
- Installation : offline installer

---

## Pourquoi HTTP et pas HTTPS ?

HTTPS nécessite un certificat SSL valide. Pour des IPs
locales comme 192.168.157.20 il n'existe pas de certificat
public. Un certificat auto-signé créerait des complications
car Docker et les outils le refusent par défaut.

En production Harbor tourne toujours en HTTPS.
En lab local HTTP est acceptable car le réseau est
privé et isolé — pas exposé à internet.

---

## Installation

### 1. Créer le dossier de travail
```bash
mkdir -p ~/harbor && cd ~/harbor
```

### 2. Télécharger l'installeur offline
```bash
wget https://github.com/goharbor/harbor/releases/download/v2.10.0/harbor-offline-installer-v2.10.0.tgz
```

**Pourquoi offline installer ?**
Harbor propose deux versions — online et offline.
L'offline télécharge toutes les images Docker en avance.
Plus fiable car pas de dépendance internet pendant
l'installation.

### 3. Extraire l'archive
```bash
tar xzvf harbor-offline-installer-v2.10.0.tgz
cd harbor
```

**`tar xzvf`** :
- `x` — extraire
- `z` — décompresser gzip
- `v` — verbose, affiche les fichiers extraits
- `f` — spécifie le fichier archive

### 4. Créer le fichier de configuration
```bash
cp harbor.yml.tmpl harbor.yml
nano harbor.yml
```

**Modifications à faire dans harbor.yml :**

**Modification 1 — hostname**
```yaml
# Avant
hostname: reg.mydomain.com

# Après
hostname: 192.168.157.20
```

**Modification 2 — Désactiver HTTPS**
```yaml
# Commenter tout le bloc https
# https:
#   port: 443
#   certificate: /your/certificate/path
#   private_key: /your/private/key/path
```

**`#`** en YAML = commentaire, la ligne est ignorée.

### 5. Lancer l'installation
```bash
sudo ./install.sh
```

Harbor installe automatiquement tous ses containers
via Docker Compose.

---

## Containers Harbor installés

| Container | Rôle |
|-----------|------|
| harbor-core | Logique métier principale |
| harbor-portal | Interface web |
| harbor-db | Base de données PostgreSQL |
| harbor-jobservice | Gestion des tâches asynchrones |
| harbor-log | Centralisation des logs |
| harbor-registryctl | Contrôle du registry |
| registry | Stockage des images |
| redis | Cache et sessions |
| nginx | Reverse proxy |

---

## Configuration post-installation

### Accès initial
URL : http://192.168.157.20
Login : admin
Mot de passe : Harbor12345 (à changer immédiatement)

⚠️ Sauvegarder le nouveau mot de passe dans KeePass.

### Créer le projet securebank

**Chemin exact :**
Projets → Nouveau projet

Paramètres :
- Nom : securebank
- Niveau d'accès : Privé (case Public décochée)
- Project quota limits : -1 (illimité)
- Proxy Cache : désactivé

**Pourquoi privé ?**
En fintech on ne veut jamais un registry public.
Seuls les utilisateurs autorisés peuvent pousser
et tirer des images.

**Quota -1 ?**
-1 = illimité. Pas de limite de stockage pour le lab.
En entreprise on fixe une limite pour éviter qu'un
projet ne remplisse tout le disque.

### Activer le scan automatique
Projet securebank → Configuration → Scanner automatique ✅

Chaque image poussée est automatiquement scannée
pour détecter des CVE.

---

## Vérification finale
- Harbor accessible : http://192.168.157.20 ✅
- Connexion admin : ✅
- Projet securebank créé : ✅
- Scan automatique activé : ✅

---

## Statut
- [x] Harbor v2.10.0 installé ✅
- [x] Projet securebank créé ✅
- [x] Scan automatique activé ✅
- [x] Snapshot sonarqube-harbor-ready ✅
