import subprocess
import re

import yaml
from flask import Flask, request, jsonify

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/load-config")
def load_config():
    """
    VULNERÁVEL DE PROPÓSITO — Deserialização insegura (CWE-502).
    yaml.load() sem Loader seguro permite construir objetos Python arbitrários
    a partir do YAML enviado pelo cliente (equivalente a RCE em casos reais).
    Objetivo: dar ao Snyk Code (SAST) / Bandit um achado real para a demo.
    Não usar em produção.
    """
    raw = request.get_data(as_text=True)
    data = yaml.load(raw, Loader=yaml.Loader)  # nosec - vulnerável de propósito
    return jsonify(loaded=str(data))


@app.get("/load-config-safe")
def load_config_safe_info():
    return jsonify(hint="use POST /load-config-safe com corpo YAML")


@app.post("/load-config-safe")
def load_config_safe():
    """Versão SEGURA: yaml.safe_load só constrói tipos nativos do Python."""
    raw = request.get_data(as_text=True)
    data = yaml.safe_load(raw)
    return jsonify(loaded=str(data))


@app.get("/ping-vulnerable")
def ping_vulnerable():
    """
    VULNERÁVEL DE PROPÓSITO — Command Injection (CWE-78).
    shell=True + concatenação direta da entrada do usuário.
    Objetivo: achado clássico de SAST (Snyk Code / Bandit B602/B605).
    Não usar em produção.
    """
    host = request.args.get("host", "localhost")
    result = subprocess.run(
        f"ping -c 1 {host}", shell=True, capture_output=True, text=True
    )  # nosec - vulnerável de propósito
    return jsonify(output=result.stdout)


@app.get("/ping-safe")
def ping_safe():
    """Versão SEGURA: validação de entrada + sem shell=True."""
    host = request.args.get("host", "localhost")
    if not re.match(r"^[a-zA-Z0-9.-]+$", host):
        return jsonify(error="invalid host"), 400

    result = subprocess.run(
        ["ping", "-c", "1", host], capture_output=True, text=True
    )
    return jsonify(output=result.stdout)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
