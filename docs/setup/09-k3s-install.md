# 09 — Installation k3s (Kubernetes)

## Objectif
Installation et configuration de k3s sur vm-k3s.
k3s est la distribution Kubernetes légère utilisée
comme environnement de test local avant déploiement
sur AWS EKS en production.

## Concept clé — Kubernetes

Kubernetes c'est le système d'orchestration de containers
le plus utilisé en entreprise. Il gère automatiquement :
- Le déploiement des applications containerisées
- La mise à l'échelle (plus de trafic = plus de containers)
- La disponibilité (un container tombe = il est remplacé)
- Le réseau entre les containers

### Pourquoi k3s et pas Kubernetes complet ?
Kubernetes standard nécessite beaucoup de ressources.
k3s c'est la même chose mais optimisé pour les
environnements avec peu de ressources comme nos VMs.
En production on utilisera AWS EKS (Kubernetes complet).

k3s = environnement de test local
AWS EKS = environnement de production

## Environnement
- VM : vm-k3s (192.168.157.40)
- k3s version : v1.34.4+k3s1
- Installation : script officiel

---

## Concepts Kubernetes essentiels

**Node** — une machine (VM ou serveur) dans le cluster.

**Pod** — la plus petite unité dans Kubernetes.
Un ou plusieurs containers qui tournent ensemble.

**Deployment** — dit à Kubernetes "je veux X copies
de ce Pod, maintiens les toujours".

**Service** — expose un Pod sur le réseau pour
qu'il soit accessible depuis l'extérieur.

**Namespace** — espace isolé dans le cluster.
Comme des dossiers pour organiser les ressources.

---

## Installation

### 1. Installer k3s
```bash
curl -sfL https://get.k3s.io | sh -
```

Le script officiel installe Kubernetes + tous ses
composants automatiquement en une seule commande.

`-sfL` :
- `s` — silencieux
- `f` — échoue proprement en cas d'erreur
- `L` — suit les redirections HTTP

### 2. Vérifier l'installation
```bash
sudo kubectl get nodes
```

Résultat attendu :
```
NAME     STATUS   ROLES           AGE   VERSION
vm-k3s   Ready    control-plane   Xm    v1.34.4+k3s1
```

---

## Configuration kubectl sans sudo

### Pourquoi cette configuration ?
k3s crée son fichier de configuration dans
`/etc/rancher/k3s/k3s.yaml` — accessible uniquement
par root. Sans configuration, kubectl nécessite sudo.

**Le kubeconfig** c'est le fichier qui contient :
- L'adresse du serveur Kubernetes
- Le certificat pour la connexion sécurisée
- Les credentials d'authentification

Sans ce fichier kubectl ne sait pas où est le cluster.

### 1. Copier le kubeconfig
```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown hicham:hicham ~/.kube/config
```

On copie le fichier dans le dossier personnel de hicham
et on lui donne les droits dessus.

### 2. Donner les permissions sur le fichier original
```bash
sudo chmod 644 /etc/rancher/k3s/k3s.yaml
```

`644` — le propriétaire peut lire/écrire,
les autres peuvent juste lire.

### 3. Rendre KUBECONFIG permanent
```bash
echo 'export KUBECONFIG=~/.kube/config' >> ~/.bashrc
source ~/.bashrc
```

`~/.bashrc` — fichier exécuté à chaque ouverture
de terminal. Tout ce qu'on y ajoute est chargé
automatiquement.

`source ~/.bashrc` — recharge le fichier immédiatement.

### 4. Vérifier sans sudo
```bash
kubectl get nodes
```

---

## Création du namespace SecureBank

```bash
kubectl create namespace securebank
```

**Pourquoi un namespace dédié ?**
En Kubernetes on sépare les applications par namespace.
Tous les pods, services et déploiements SecureBank
vivront dans ce namespace — isolés des autres
applications et des composants système.

### Les namespaces système

| Namespace | Rôle |
|-----------|------|
| default | Namespace par défaut — ne jamais utiliser en prod |
| kube-system | Composants internes Kubernetes — ne jamais toucher |
| kube-public | Ressources publiques accessibles par tous |
| kube-node-lease | Gestion disponibilité des nodes |
| securebank | Notre namespace ✅ |

### Vérifier les namespaces
```bash
kubectl get namespaces
```

---

## Vérification finale
- k3s installé : v1.34.4+k3s1 ✅
- Node vm-k3s Ready ✅
- kubectl sans sudo ✅
- KUBECONFIG permanent ✅
- Namespace securebank créé ✅

---

## Statut
- [x] k3s installé ✅
- [x] kubectl configuré sans sudo ✅
- [x] Namespace securebank créé ✅
