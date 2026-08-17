# Imagem base propositalmente desatualizada para o Trivy encontrar CVEs de SO
FROM python:3.14-slim

# Sem isso, o stdout do container fica bufferizado e o print() de
# /load-config (a prova de execução de código) não aparece em `docker logs`.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

EXPOSE 5000

# Rodando como root de propósito — Trivy (misconfig) deve sinalizar isso.
# Correção sugerida:
# RUN useradd -m appuser
# USER appuser

CMD ["python", "src/app.py"]
