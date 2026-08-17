import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_ping_safe_rejeita_host_invalido(client):
    res = client.get("/ping-safe", query_string={"host": "; rm -rf /"})
    assert res.status_code == 400


def test_ping_safe_aceita_host_valido(client):
    res = client.get("/ping-safe", query_string={"host": "localhost"})
    assert res.status_code == 200


def test_load_config_safe_com_yaml_legitimo(client):
    res = client.post("/load-config-safe", data="theme: dark\n")
    assert res.status_code == 200
    assert "dark" in res.get_json()["loaded"]


def test_load_config_demonstra_deserializacao_insegura(client, capsys):
    """
    Regressão de segurança: comprova, na prática, que o endpoint /load-config
    (yaml.load com Loader inseguro, na versão PyYAML==5.1 fixada no projeto)
    permite instanciar objetos Python arbitrários a partir do YAML recebido —
    exatamente o tipo de achado que o Snyk/Bandit reportam para essa combinação
    de biblioteca vulnerável + uso inseguro no código.

    O payload aqui é inofensivo (só chama print), mas prova a execução de
    código arbitrário durante a desserialização.
    """
    payload = "!!python/object/apply:builtins.print ['insecure deserialization executada']"

    client.post("/load-config", data=payload)

    captured = capsys.readouterr()
    assert "insecure deserialization executada" in captured.out
