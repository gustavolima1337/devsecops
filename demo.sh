#!/usr/bin/env bash
set -uo pipefail

echo "== 1/6 Instalando dependências (Python) =="
pip install --user -r requirements-dev.txt

echo
echo "== 2/6 Rodando testes unitários (pytest) =="
python3 -m pytest -v

echo
echo "== 3/6 Snyk - SCA (dependências do requirements.txt) =="
if command -v snyk >/dev/null; then
  snyk test --file=requirements.txt --package-manager=pip --severity-threshold=medium \
    || echo "[Snyk] Vulnerabilidades encontradas (esperado - Flask/PyYAML/requests estão desatualizados de propósito)"
else
  echo "[aviso] snyk CLI não instalado. Instale com: npm install -g snyk && snyk auth"
fi

echo
echo "== 4/6 Snyk Code - SAST (análise estática do código-fonte) =="
if command -v snyk >/dev/null; then
  snyk code test \
    || echo "[Snyk Code] Problemas encontrados (esperado - yaml.load inseguro e command injection em src/app.py)"
fi

echo
echo "== 5/6 Build da imagem Docker =="
docker build -t devsecops-demo:local .

echo
echo "== 6/6 Trivy - scan da imagem e da configuração (Dockerfile) =="
if command -v trivy >/dev/null; then
  echo "--- Scan da imagem (CVEs de SO + libs Python) ---"
  trivy image --severity HIGH,CRITICAL devsecops-demo:local || true
  echo
  echo "--- Scan de configuração/IaC (Dockerfile) ---"
  trivy config . || true
else
  echo "[aviso] trivy não instalado. Veja: https://aquasecurity.github.io/trivy/latest/getting-started/installation/"
fi

echo
echo "Demo concluída. Veja os relatórios acima."
