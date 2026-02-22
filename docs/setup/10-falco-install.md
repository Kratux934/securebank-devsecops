# 10 — Installation Falco

## Objectif
Installation et configuration de Falco sur vm-k3s.
Falco est l'outil de sécurité runtime du projet — il
surveille en temps réel ce qui se passe dans les
containers et détecte les comportements suspects.

## Concept clé — Sécurité Runtime

Falco c'est la **dernière ligne de défense** du pipeline.
Même si un attaquant passe à travers toutes les autres
couches de sécurité (SAST, SCA, scan d'image), Falco
le détecte en temps réel quand il agit dans un container.

Exemples de ce que Falco détecte :
- Un container qui essaie d'écrire dans /etc
- Un processus qui ouvre un shell dans un container
- Une connexion réseau suspecte depuis un pod
- Un container qui tourne en root alors qu'il ne devrait pas
- Un fichier sensible lu par un processus non autorisé

## Environnement
- VM : vm-k3s (192.168.157.40)
- Falco version : latest
- Driver : modern eBPF
- Installation : apt via repo officiel Falco

---

## Concept — eBPF et modern eBPF

**eBPF** (extended Berkeley Packet Filter) est une
technologie du kernel Linux qui permet à Falco de
surveiller les appels système sans modifier le kernel.

**modern eBPF** — version la plus récente, plus stable
et plus performante. Falco 0.38+ la choisit automatiquement
sur les kernels Linux récents.

---

## Installation via repo officiel Falco

### 1. Ajouter la clé GPG officielle Falco
```bash
curl -fsSL https://falco.org/repo/falcosecurity-packages.asc | sudo gpg --dearmor -o /usr/share/keyrings/falco-archive-keyring.gpg
```

`curl -fsSL` — télécharge la clé GPG depuis falco.org
`gpg --dearmor` — convertit du format texte en binaire
`/usr/share/keyrings/` — dossier des clés de confiance apt

### 2. Ajouter le repo officiel Falco
```bash
echo "deb [signed-by=/usr/share/keyrings/falco-archive-keyring.gpg] https://download.falco.org/packages/deb stable main" | sudo tee /etc/apt/sources.list.d/falcosecurity.list
```

### 3. Installer Falco
```bash
sudo apt update && sudo apt install -y falco
```

Falco choisit automatiquement **modern-bpf** sur
les kernels récents — pas besoin de configuration manuelle.

---

## Ce que Falco installe automatiquement

- `falco-modern-bpf.service` — service systemd
- `/etc/falco/falco_rules.yaml` — règles de détection par défaut
- `/etc/falco/falco_rules.local.yaml` — fichier pour nos règles custom

---

## Concept — Les règles Falco

Falco fonctionne avec des règles YAML. Chaque règle
définit un comportement suspect à détecter.

Exemple de règle :
```yaml
- rule: Shell spawned in container
  desc: Un shell a été ouvert dans un container
  condition: container and proc.name = bash
  output: "Shell ouvert (user=%user.name container=%container.name)"
  priority: WARNING
```

**`condition`** — quand déclencher l'alerte
**`output`** — message de l'alerte avec variables dynamiques
**`priority`** — niveau de sévérité (DEBUG, INFO, WARNING, ERROR, CRITICAL)

Falco a des centaines de règles par défaut.
On créera des règles custom pour SecureBank en Phase 6.

---

## Vérification

```bash
sudo systemctl status falco
```

Résultats attendus :
- active (running) ✅
- enabled ✅
- engine.kind=modern_ebpf ✅
- Loading rules from /etc/falco/falco_rules.yaml ✅
- Enabled event sources: syscall ✅

---

## Vérification finale
- Falco installé et running ✅
- Driver modern eBPF ✅
- Règles par défaut chargées ✅
- Service enabled au démarrage ✅

---

## Statut
- [x] Falco installé via repo officiel ✅
- [x] Driver modern eBPF actif ✅
- [x] Snapshot k3s-falco-ready ✅
