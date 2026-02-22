# Stage 1 — Build
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2 — Production
FROM python:3.11-slim

# Créer un utilisateur non-root
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser

WORKDIR /app

# Copier les dépendances installées depuis le stage builder
COPY --from=builder /root/.local /home/appuser/.local

# Copier le code
COPY --chown=appuser:appgroup main.py .

# Utiliser l'utilisateur non-root
USER appuser

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
