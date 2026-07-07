# ---- builder: install dependencies ----
FROM python:3.11-slim AS builder

WORKDIR /app

COPY pyproject.toml ./

RUN pip install --no-cache-dir flask pyyaml python-dotenv psutil

# Default CMD for the dev compose (target: builder) — source is bind-mounted
CMD ["python3", "wol_server.py"]

# ---- production image ----
FROM python:3.11-slim

WORKDIR /app

# Carry the installed packages from the builder stage
COPY --from=builder /usr/local /usr/local

COPY wol_server.py wol_manager.py ./
COPY templates/ templates/
COPY static/ static/

RUN mkdir -p data security

ENV WOL_HOST=0.0.0.0 \
    WOL_PORT=5000 \
    PYTHONUNBUFFERED=1

EXPOSE 5000

CMD ["python3", "wol_server.py"]
