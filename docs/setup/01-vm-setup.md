# 01 — VM Setup (Infrastructure Locale)

## Objectif
Création et configuration des 4 VMs Ubuntu Server 24.04 
sur VMware Workstation qui constituent l'environnement 
DevSecOps local.

## Environnement
- Hyperviseur : VMware Workstation 17.5
- OS : Ubuntu Server 24.04.3 LTS
- Réseau : VMnet8 (NAT) — 192.168.157.0/24

## Plan d'adressage IP

| VM | IP Fixe | Rôle |
|----|---------|------|
| vm-gitlab | 192.168.157.10 | GitLab CE + Runner |
| vm-security | 192.168.157.20 | SonarQube + Harbor + OWASP DT |
| vm-vault | 192.168.157.30 | Vault + Grafana + Prometheus + Loki |
| vm-k3s | 192.168.157.40 | k3s + Falco |

## Configuration de chaque VM

### Ressources allouées

| VM | RAM | CPU | Disque |
|----|-----|-----|--------|
| vm-gitlab | 6GB | 4 vCPU | 50GB |
| vm-security | 8GB | 4 vCPU | 60GB |
| vm-vault | 4GB | 2 vCPU | 40GB |
| vm-k3s | 6GB | 4 vCPU | 40GB |

## Procédure d'installation (répétée sur chaque VM)

### 1. Configuration IP fixe
```bash
sudo nano /etc/netplan/50-cloud-init.yaml
```

Contenu du fichier :
```yaml
network:
  version: 2
  ethernets:
    ens33:
      dhcp4: false
      addresses:
        - 192.168.157.X/24
      routes:
        - to: default
          via: 192.168.157.2
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Appliquer la configuration :
```bash
sudo netplan apply
```

### 2. Mise à jour système
```bash
sudo apt update && sudo apt upgrade -y
```

### 3. Installation des outils de base
```bash
sudo apt install -y curl wget git vim net-tools htop unzip
```

## Pourquoi ces choix techniques

**Ubuntu Server 24.04 LTS** — version Long Term Support, 
supportée jusqu'en 2029. Stable et utilisée en entreprise.

**IP fixe** — indispensable pour que les VMs se trouvent 
toujours à la même adresse. Avec DHCP l'IP peut changer 
au redémarrage et tout le lab casse.

**NAT VMnet8** — les VMs ont accès à internet via le PC 
host pour télécharger les outils, et se parlent entre elles 
sur le réseau privé 192.168.157.0/24.

**SSH activé** — permet de travailler depuis un terminal 
Windows (Windows Terminal) plutôt que dans la fenêtre VMware.
Beaucoup plus confortable et proche d'un environnement réel.

## Statut

- [x] vm-gitlab — 192.168.157.10 ✅
- [x] vm-security — 192.168.157.20 ✅
- [x] vm-vault — 192.168.157.30 ✅
- [x] vm-k3s — 192.168.157.40 ✅
