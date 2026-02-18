# 🏦 SecureBank — DevSecOps Cloud-Native Platform

> Enterprise-grade DevSecOps platform for a fictional fintech, reproducing a real production environment with a fully secured CI/CD pipeline, supply chain security, Kubernetes hardening, and AWS cloud-native security.

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [Architecture](#-architecture)
- [Security Pipeline](#-security-pipeline)
- [Tech Stack](#-tech-stack)
- [Infrastructure](#-infrastructure)
- [Security Controls](#-security-controls)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [Threat Model](#-threat-model)
- [Certifications](#-certifications)

---

## 🎯 Project Overview

SecureBank is a fictional fintech platform built to demonstrate a **complete DevSecOps lifecycle** from code to production. The project simulates a real enterprise environment where security is embedded at every stage of the software delivery chain.

### The Application

Three microservices simulating core banking operations:

| Service | Role | Tech |
|---------|------|------|
| `auth-service` | Authentication & JWT token management | Python FastAPI |
| `account-service` | Account management & balance queries | Python FastAPI |
| `transaction-service` | Fund transfers between accounts | Python FastAPI |

### What this project demonstrates

- **Shift-left security** — security starts before the first line of code is pushed
- **Supply chain security** — every dependency, image, and artifact is tracked and verified
- **Zero-trust Kubernetes** — no workload is trusted by default
- **Secrets management** — no secret ever touches the codebase or environment variables
- **Runtime security** — suspicious behavior is detected in real time in production

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     LOCAL ENVIRONMENT                        │
│                                                             │
│  ┌──────────┐  ┌────────────┐  ┌─────────┐  ┌──────────┐  │
│  │  GitLab  │  │ SonarQube  │  │  Vault  │  │  Harbor  │  │
│  │  CI/CD   │  │   SAST     │  │ Secrets │  │ Registry │  │
│  └──────────┘  └────────────┘  └─────────┘  └──────────┘  │
│                                                             │
│  ┌──────────┐  ┌────────────┐  ┌─────────────────────────┐ │
│  │  OWASP   │  │  Grafana   │  │         k3s             │ │
│  │    DT    │  │ Prometheus │  │   (dev/test cluster)    │ │
│  │   SCA    │  │    Loki    │  │                         │ │
│  └──────────┘  └────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ Pipeline
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      AWS ENVIRONMENT                         │
│                                                             │
│  ┌──────────┐  ┌─────────┐  ┌──────────┐  ┌────────────┐  │
│  │   ECR    │  │   KMS   │  │   IAM    │  │     S3     │  │
│  │ Registry │  │Signing  │  │ Least    │  │  Artifacts │  │
│  │          │  │ Cosign  │  │Privilege │  │    Logs    │  │
│  └──────────┘  └─────────┘  └──────────┘  └────────────┘  │
│                                                             │
│  ┌──────────────────────────┐  ┌──────────┐  ┌──────────┐  │
│  │           EKS            │  │GuardDuty │  │Security  │  │
│  │  (production cluster)    │  │          │  │   Hub    │  │
│  │  Kyverno + Falco + RBAC  │  │          │  │          │  │
│  └──────────────────────────┘  └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔐 Security Pipeline

Every code push triggers the following security gates — **any failure blocks the pipeline**:

```
Git Push
│
├── 🔍 Pre-commit
│   ├── git-secret          → blocks hardcoded secrets
│   ├── GitLeaks            → deep secret scanning
│   └── detect-secrets      → entropy-based detection
│
├── 📊 Stage 1 — SAST
│   ├── SonarQube           → Quality Gate (blocking)
│   └── Semgrep             → custom fintech security rules
│
├── 📦 Stage 2 — SCA
│   ├── Trivy fs scan       → dependency vulnerabilities
│   └── OWASP DT            → CVE tracking over time
│
├── 🐳 Stage 3 — Build
│   └── Docker              → multi-stage, non-root
│
├── 🔬 Stage 4 — Image Security
│   ├── Trivy image scan    → CVE scan (CRITICAL blocks)
│   ├── Syft                → SBOM generation (CycloneDX)
│   └── OWASP DT            → SBOM ingestion
│
├── ✍️  Stage 5 — Sign & Push
│   ├── Cosign + AWS KMS    → image signing
│   ├── Harbor              → local registry (dev)
│   └── AWS ECR             → production registry
│
├── 🚀 Stage 6 — Deploy EKS
│   ├── Helm                → deployment
│   ├── Kyverno             → blocks unsigned images
│   └── Vault Agent         → secrets injection
│
└── 🧪 Stage 7 — Post-Deploy
    ├── OWASP ZAP           → DAST scan
    ├── Falco               → runtime monitoring
    └── AWS Security Hub    → posture report
```

---

## 🛠️ Tech Stack

### Security Tools

| Category | Tool | Purpose |
|----------|------|---------|
| SAST | SonarQube, Semgrep | Static code analysis |
| SCA | Trivy, OWASP Dependency-Track | Dependency vulnerabilities |
| Secret Scanning | GitLeaks, git-secret, detect-secrets | Prevent secret leaks |
| SBOM | Syft, CycloneDX | Software bill of materials |
| Image Signing | Cosign + AWS KMS | Supply chain integrity |
| Registry | Harbor (local), AWS ECR (prod) | Image storage |
| Admission Control | Kyverno | K8s policy enforcement |
| Secrets Management | HashiCorp Vault + AWS KMS | Zero-secret codebase |
| Runtime Security | Falco | Threat detection in prod |
| DAST | OWASP ZAP | Dynamic application testing |
| Cloud Security | AWS GuardDuty, Security Hub | Cloud posture management |

### Infrastructure & Observability

| Category | Tool | Purpose |
|----------|------|---------|
| CI/CD | GitLab CE + GitLab Runner | Pipeline orchestration |
| Container Orchestration | Kubernetes (k3s + EKS) | Workload management |
| IaC | Terraform | AWS infrastructure |
| Configuration | Ansible | VM provisioning |
| Metrics | Prometheus + Grafana | Observability |
| Logs | Loki + Promtail | Log aggregation |
| Alerting | Alertmanager | Security alerts |

---

## 🖥️ Infrastructure

### Local Environment (VMware Workstation)

| VM | Role | RAM | CPU |
|----|------|-----|-----|
| vm-gitlab | GitLab CE + Runner | 6GB | 4 vCPU |
| vm-security | SonarQube + OWASP DT + Harbor | 8GB | 4 vCPU |
| vm-vault | Vault + Grafana + Prometheus + Loki | 4GB | 2 vCPU |
| vm-k3s | k3s cluster + Falco | 6GB | 4 vCPU |

### AWS Environment

| Service | Usage |
|---------|-------|
| EKS | Production Kubernetes cluster |
| ECR | Production container registry |
| KMS | Cosign signing key + Vault encryption |
| IAM | Least privilege policies + IRSA |
| S3 | Artifacts, logs, SBOM storage |
| GuardDuty | Threat detection |
| Security Hub | Security posture dashboard |

---

## 🛡️ Security Controls

### Kubernetes Hardening

- **RBAC** — least privilege roles for every service account
- **Network Policies** — default deny, explicit allow only
- **Pod Security Standards** — restricted profile enforced
- **Admission Control** — Kyverno blocks any unsigned or non-compliant image
- **Secrets** — injected by Vault Agent, never in manifests or env vars

### AWS Security

- **IAM** — fine-grained JSON policies, zero wildcard permissions
- **IRSA** — pods authenticate to AWS via service account, no static credentials
- **KMS** — all secrets encrypted at rest, signing key never leaves KMS
- **S3** — no public access, versioning enabled, encrypted
- **GuardDuty** — enabled on all regions
- **Security Hub** — CIS AWS Foundations benchmark enforced

### Supply Chain

- Every image is **signed with Cosign** before being pushed
- Every image has a **SBOM** stored and tracked in OWASP DT
- **Kyverno verifies the Cosign signature** before any pod starts
- No unsigned image can ever reach production

---

## 🚀 Getting Started

```bash
# Clone the repository
git clone https://github.com/Kratux934/securebank-devsecops.git
cd securebank-devsecops

# Start the application locally
docker compose up -d

# Access the services
# auth-service        → http://localhost:8001
# account-service     → http://localhost:8002
# transaction-service → http://localhost:8003
```

> Full setup documentation available in [docs/setup/](docs/setup/)

---

## 📁 Project Structure

```
securebank-devsecops/
├── app/
│   ├── auth-service/
│   ├── account-service/
│   └── transaction-service/
├── infrastructure/
│   ├── terraform/aws/
│   └── ansible/
├── kubernetes/
│   ├── helm/
│   ├── policies/kyverno/
│   ├── network-policies/
│   └── rbac/
├── security/
│   ├── vault/
│   ├── cosign/
│   ├── sbom/
│   └── falco/rules/
├── monitoring/
│   ├── prometheus/
│   ├── grafana/dashboards/
│   └── loki/
├── runbooks/
│   ├── secret-rotation.md
│   ├── pipeline-debug.md
│   ├── rollback.md
│   └── incident-response.md
└── docs/
    ├── setup/
    └── architecture-diagram.png
```

---

## ⚔️ Threat Model

STRIDE threat modeling applied to the CI/CD pipeline.
Full analysis available in [THREAT-MODEL.md](THREAT-MODEL.md)

| Threat | Vector | Mitigation |
|--------|--------|-----------|
| Spoofing | Fake image in registry | Cosign signature + Kyverno verification |
| Tampering | Modified image after build | Cosign + KMS immutable signing |
| Repudiation | No audit trail | GitLab audit logs + S3 artifact storage |
| Info Disclosure | Secrets in code | GitLeaks + Vault + KMS encryption |
| DoS | Pipeline resource exhaustion | GitLab resource limits + K8s quotas |
| Elevation of Privilege | Container running as root | Pod Security Standards + non-root Dockerfile |

---

## 📜 Certifications

This project is built in parallel with the following certifications:

| Certification | Status | Relevance |
|---------------|--------|-----------|
| CKA — Certified Kubernetes Administrator | 🔄 In progress | Kubernetes management |
| AWS Solutions Architect Associate | 🔄 Planned | AWS foundations |
| AWS Security Specialty | 🔄 Planned | Cloud security |
| CKS — Certified Kubernetes Security Specialist | 🔄 Planned | K8s security hardening |

---

## 👤 Author

**Hicham Khadda**
[GitHub](https://github.com/Kratux934) · [LinkedIn](#)

---

> *This project is a fictional lab environment built for learning and portfolio purposes. SecureBank is not a real company.*
