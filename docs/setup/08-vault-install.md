# 08 — Installation HashiCorp Vault

## Objectif
Installation et configuration de HashiCorp Vault sur vm-vault.
Vault est l'outil de gestion des secrets du projet — il
centralise tous les secrets et les distribue de façon
sécurisée aux applications et au pipeline CI/CD.

## Concept clé — Gestion des secrets
Un "secret" c'est tout ce qui est sensible :
mots de passe, tokens API, clés SSH, certificats,
clés de chiffrement.

Sans Vault les secrets sont souvent hardcodés dans le code
ou stockés en clair dans des variables d'environnement
— faille de sécurité majeure.

Vault centralise tous les secrets :
- Les applications demandent leurs secrets à Vault au démarrage
- Vault vérifie l'identité de l'application
- Vault retourne le secret chiffré
- Le secret n'est jamais stocké dans le code ou le pipeline

## Environnement
- VM : vm-vault (192.168.157.30)
- Vault version : v1.21.3
- Port : 8200
- Installation : apt via repo officiel HashiCorp
- Storage : file (local)

---

## Installation via repo officiel HashiCorp

### Pourquoi passer par le repo officiel ?
HashiCorp signe cryptographiquement ses paquets avec GPG.
En ajoutant leur repo officiel + clé GPG, apt vérifie
automatiquement l'authenticité de chaque paquet installé.

### 1. Installer GPG
```bash
sudo apt install -y gpg
```

GPG = GNU Privacy Guard. Outil de cryptographie qui
permet de vérifier les signatures numériques des paquets.

### 2. Télécharger la clé publique GPG HashiCorp
```bash
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
```

HashiCorp signe leurs paquets avec leur clé privée secrète.
On télécharge leur clé publique pour pouvoir vérifier
ces signatures.

`wget -O-` — télécharge et envoie en sortie directement
`gpg --dearmor` — convertit du format texte en binaire
`/usr/share/keyrings/` — dossier des clés de confiance apt

### 3. Ajouter le repo officiel HashiCorp
```bash
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
```

`signed-by=...` — indique à apt quelle clé utiliser
`lsb_release -cs` — retourne automatiquement `noble` (Ubuntu 24.04)

### 4. Installer Vault
```bash
sudo apt update && sudo apt install -y vault
```

---

## Configuration de Vault

### 1. Créer les dossiers
```bash
sudo mkdir -p /etc/vault.d
sudo mkdir -p /opt/vault/data
```

`/etc/vault.d` — configuration de Vault
`/opt/vault/data` — données chiffrées de Vault sur disque

### 2. Créer le fichier de configuration
```bash
sudo nano /etc/vault.d/vault.hcl
```

Contenu :
```hcl
ui = true

storage "file" {
  path = "/opt/vault/data"
}

listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1
}

api_addr = "http://192.168.157.30:8200"
```

`ui = true` — active l'interface web
`storage "file"` — stockage sur disque local
`tls_disable = 1` — HTTP pour le lab (HTTPS en production)
`api_addr` — adresse publique de Vault

### 3. Permissions sur les dossiers
```bash
sudo chown -R vault:vault /opt/vault/data
sudo chown -R vault:vault /etc/vault.d
```

Vault tourne avec son propre utilisateur système `vault`
— bonne pratique de sécurité, pas de root.

### 4. Démarrer Vault
```bash
sudo systemctl enable vault
sudo systemctl start vault
```

---

## Initialisation de Vault

⚠️ Cette étape ne se fait qu'**une seule fois**.

### Configurer la variable d'environnement
```bash
export VAULT_ADDR='http://192.168.157.30:8200'
```

### Initialiser Vault
```bash
vault operator init
```

Vault génère :
- **5 unseal keys** — clés de descellement
- **1 root token** — token d'accès root

⚠️ **CRITIQUE** — Sauvegarder immédiatement les 5 unseal
keys ET le root token dans KeePass. Si perdus, toutes
les données Vault sont irrécupérables définitivement.

---

## Concept — Shamir's Secret Sharing

Vault démarre toujours en mode **sealed** (scellé).
Il faut **3 clés sur 5** pour le desceller.

Pourquoi 3 sur 5 ? C'est le principe de Shamir's Secret
Sharing — les 5 clés sont des fragments d'une clé maître.
3 fragments suffisent à reconstruire la clé maître.

En entreprise 5 personnes différentes gardent chacune
une clé — personne n'a le contrôle total seul.

### Desceller Vault (à faire après chaque reboot)
```bash
vault operator unseal  # clé 1
vault operator unseal  # clé 2
vault operator unseal  # clé 3
```

Résultat attendu : `Sealed: false`

### Se connecter avec le root token
```bash
vault login
```

---

## Configuration du moteur de secrets KV

### Activer le moteur KV-v2
```bash
vault secrets enable -path=securebank kv-v2
```

**KV = Key-Value** — stockage de paires clé/valeur.
**v2** — garde un historique complet des versions de
chaque secret. On peut revenir à une version précédente.

**`-path=securebank`** — tous les secrets du projet
seront organisés sous `securebank/`.

---

## Organisation des secrets

Convention : un chemin par service ou plateforme.

```
securebank/database   →  credentials base de données
securebank/harbor     →  credentials Harbor registry
securebank/gitlab     →  tokens GitLab
securebank/sonarqube  →  token SonarQube
securebank/aws        →  credentials AWS (Phase 5)
securebank/api-keys   →  clés API externes
```

### Créer un secret
```bash
vault kv put securebank/database \
  username="securebank_user" \
  password="SecureBank@2026!" \
  host="localhost" \
  port="5432"
```

### Lister les secrets
```bash
vault kv list securebank/
```

### Lire un secret
```bash
vault kv get securebank/database
```

---

## Secrets créés pour SecureBank

| Chemin | Contenu |
|--------|---------|
| securebank/database | username, password, host, port |
| securebank/harbor | username, password, url |
| securebank/sonarqube | url, token (à compléter) |
| securebank/gitlab | url, token (à compléter) |

Les tokens SonarQube et GitLab seront mis à jour
lors de la configuration des pipelines.

---

## Vérification finale
- Vault accessible : http://192.168.157.30:8200 ✅
- Vault initialisé et descellé : ✅
- Moteur KV securebank activé : ✅
- Secrets de base créés : ✅

---

## ⚠️ Important — Vault après reboot
Vault se rescelle automatiquement à chaque reboot.
Il faut le desceller manuellement avec 3 clés sur 5 :
```bash
export VAULT_ADDR='http://192.168.157.30:8200'
vault operator unseal  # 3 fois avec 3 clés différentes
```

---

## Statut
- [x] Vault v1.21.3 installé ✅
- [x] Vault initialisé et descellé ✅
- [x] Moteur KV-v2 securebank activé ✅
- [x] Secrets de base créés ✅
- [x] Snapshot vault-ready ✅
