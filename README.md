# DevSecOps Pipeline Demo — Snyk + Trivy + Dependabot

Projeto de demonstração de uma esteira DevSecOps completa, usando um app Flask
(Python) com dependências e trechos de código **propositalmente vulneráveis**,
para que Snyk e Trivy tenham algo real para encontrar durante a demo.

⚠️ Uso educacional/demonstração de tooling de segurança. Não faça deploy deste
código como está.

## Estrutura

```
.
├── src/app.py                 # app Flask com endpoints vulneráveis + versões seguras
├── tests/test_app.py          # testes funcionais + regressão de segurança (pytest)
├── requirements.txt           # deps com versões antigas (achados para Snyk SCA/Trivy)
├── Dockerfile                 # HEALTHCHECK, usuário não-root (fix aplicado via Trivy IaC)
├── demo.sh                    # roda tudo localmente (testes + snyk + trivy)
├── .github/workflows/
│   ├── devsecops.yml          # a esteira em si (CI)
│   └── dependabot-auto-merge.yml
└── .github/dependabot.yml     # atualização automática de deps/imagem/actions
```

## Onde está cada vulnerabilidade (de propósito)

| Local | Tipo | Detectado por |
|---|---|---|
| `requirements.txt` (PyYAML 5.1, requests 2.19.1) | Dependências com CVEs conhecidas (ex.: CVE-2019-20477 no PyYAML) | **Snyk SCA** (`snyk test`), Trivy (`trivy fs`) |
| `src/app.py :: /load-config` | Desserialização insegura (`yaml.load` sem safe loader) | **Snyk Code** (SAST) |
| `src/app.py :: /ping-vulnerable` | Command Injection (`shell=True` + concatenação) | **Snyk Code** (SAST) |
| ~~`Dockerfile` rodando como root~~ | Má prática de container — **corrigido**: `USER appuser` + `HEALTHCHECK` adicionados após o Trivy IaC sinalizar `DS-0002` | **Trivy** (`trivy config`) |

Cada endpoint vulnerável tem uma versão `-safe` ao lado, mostrando o fix.

## Como a esteira funciona (`.github/workflows/devsecops.yml`)

```
build-and-test (pytest)
   ├── sca-snyk        → Snyk Open Source: escaneia requirements.txt
   ├── sast-snyk-code   → Snyk Code: escaneia o código-fonte (SAST)
   ├── container-trivy  → build da imagem + Trivy escaneia CVEs da imagem
   └── iac-trivy        → Trivy escaneia Dockerfile (misconfig/best practices)
        ├── snyk-monitor → snapshot contínuo no dashboard do Snyk (só em push na main)
        └── deploy        (só roda em push na main, e só se todos os gates passarem)
```

Todos os jobs publicam SARIF no GitHub Code Scanning (aba **Security**), então
os achados de Snyk e Trivy aparecem lado a lado no mesmo painel.

Para bloquear merges com vulnerabilidade alta, configure em
**Settings → Branches → Branch protection rule (main)** os checks
`sca-snyk`, `sast-snyk-code`, `container-trivy` e `iac-trivy` como obrigatórios.

## Monitoramento contínuo (o que acontece depois do deploy)

`snyk test` e `trivy image` só enxergam vulnerabilidade que **já existe** no
momento do scan. Mas CVEs novas são divulgadas todo dia em bibliotecas que
você já tem em produção há meses, sem você ter mudado uma linha de código.
Duas peças cobrem isso:

- **`snyk-monitor`** (dentro do `devsecops.yml`) — roda `snyk monitor` toda
  vez que a `main` é atualizada. Diferente do `snyk test` (que só imprime o
  resultado e sai), o `monitor` manda um snapshot das dependências pro
  dashboard do Snyk. Se uma CVE nova for divulgada depois, o Snyk te avisa
  por e-mail sem você precisar rodar nada de novo.
- **`.github/workflows/scheduled-scan.yml`** — roda sozinho todo dia às 06:00
  UTC (`cron`), independente de qualquer push. Builda a imagem a partir da
  `main` atual e roda `trivy image` nela. Se achar HIGH/CRITICAL, abre uma
  **issue automaticamente** no repositório com o link pro log e pro SARIF.
  Dá pra disparar manualmente também, pela aba Actions → "Scheduled Security
  Scan" → **Run workflow**.

## Onde entra o Dependabot (no momento do deploy)

O Dependabot (`.github/dependabot.yml`) monitora diariamente/semanalmente:
- `pip` → dependências Python (`requirements.txt`)
- `docker` → imagem base do `Dockerfile`
- `github-actions` → versões das actions usadas no pipeline

Cada PR aberto pelo Dependabot passa pelo **mesmo** `devsecops.yml` (porque o
workflow roda em `pull_request`). Ou seja: uma atualização de dependência só
pode ser mergeada — e consequentemente ir para o job `deploy` — se passar nos
mesmos gates de Snyk e Trivy. O `dependabot-auto-merge.yml` habilita merge
automático apenas para atualizações patch/minor que passem em todos os checks;
atualizações major ficam para revisão manual.

Isso fecha o ciclo: Snyk/Trivy **encontram** as vulnerabilidades, Dependabot
**corrige** automaticamente, e a esteira **garante** que só vai para produção
uma versão corrigida que passou nos mesmos scans.

## Rodando a demo localmente

Não é preciso `venv` — o script instala com `pip install --user`.

Pré-requisitos opcionais (a demo roda mesmo sem eles, avisando o que falta):
- [Snyk CLI](https://docs.snyk.io/snyk-cli): `npm install -g snyk && snyk auth`
- [Trivy](https://aquasecurity.github.io/trivy/latest/getting-started/installation/)
  (não precisa de sudo: dá pra baixar o binário standalone para `~/.local/bin`)
- Docker

```bash
cd ~/devsecops
./demo.sh
```

O script:
1. Instala as dependências Python (`pip install --user`)
2. Roda os testes unitários (`pytest`), incluindo o teste que **comprova na
   prática** a desserialização insegura do `yaml.load`
3. Roda `snyk test` contra o `requirements.txt` → deve listar CVEs do
   Flask/PyYAML/requests
4. Roda `snyk code test` contra `src/app.py` → deve apontar o command
   injection e o `yaml.load` inseguro
5. Builda a imagem Docker
6. Roda `trivy image` (CVEs de SO/libs) e `trivy config` (más práticas do
   Dockerfile, como rodar como root)

**Já validado neste ambiente**: os 5 testes do pytest passam (inclusive a
prova de execução de código via `yaml.load`), e a imagem Docker builda e roda
normalmente — rodando o container e enviando o payload malicioso para
`/load-config`, a string `rce via yaml.load` aparece de fato em `docker logs`,
comprovando a execução de código dentro do container. Só não deu para testar
`snyk`/`trivy` aqui porque as CLIs não estão instaladas neste ambiente.

## Testando os endpoints manualmente

```bash
python src/app.py
# outro terminal:
curl http://localhost:5000/health

# demonstra prototype-pollution-like deserialization (payload inofensivo, só imprime)
curl -X POST http://localhost:5000/load-config \
  --data "!!python/object/apply:builtins.print ['rce via yaml.load']"

# versão segura equivalente
curl -X POST http://localhost:5000/load-config-safe --data "theme: dark"
```
