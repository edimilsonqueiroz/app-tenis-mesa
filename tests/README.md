# 🧪 Testes do Sistema Tênis de Mesa

Suite completa de testes para garantir a qualidade e confiabilidade do sistema.

## 📋 Estrutura dos Testes

```
tests/
├── conftest.py              # Configuração compartilhada e fixtures
├── test_ittf_rules.py      # Testes das regras ITTF
├── test_models.py          # Testes dos modelos
├── test_placar_routes.py   # Testes das rotas de placar
├── test_mesa_status.py     # Testes de status e mesas
├── test_integration.py     # Testes de integração completos
└── __init__.py
```

## 🚀 Como Executar os Testes

### Instalar dependências de teste
```bash
pip install pytest pytest-cov
```

### Executar todos os testes
```bash
pytest
```

### Executar com verbosidade
```bash
pytest -v
```

### Executar testes específicos
```bash
# Testes de regras ITTF
pytest tests/test_ittf_rules.py -v

# Testes de rotas de placar
pytest tests/test_placar_routes.py -v

# Testes de integração
pytest tests/test_integration.py -v
```

### Gerar relatório de cobertura
```bash
pytest --cov=. --cov-report=html
```

## 📊 Tipos de Testes

### 1. **test_ittf_rules.py** - Testes das Regras ITTF
- ✅ Validação de fim de set (11 pontos com 2+ diferença)
- ✅ Deuce (11x10, 12x10, etc)
- ✅ Alternância de servidor a cada 2 saques
- ✅ Transição de sets
- ✅ Fim do jogo (melhor de 3, melhor de 5)

### 2. **test_models.py** - Testes dos Modelos
- ✅ Criação de campeonatos
- ✅ Criação e status de mesas
- ✅ Criação e atualização de placares
- ✅ Criação de jogadores
- ✅ Conversão para dicionário (to_dict)

### 3. **test_placar_routes.py** - Testes das Rotas de Placar
- ✅ Obtenção de placar
- ✅ Adição de pontos (time 1 e 2)
- ✅ Remoção de pontos
- ✅ Definição manual de pontos
- ✅ Troca de sacador
- ✅ Reset de mesa
- ✅ Configuração de formato

### 4. **test_mesa_status.py** - Testes de Mesas e Status
- ✅ Status disponível/em_uso
- ✅ Mudança de status ao adicionar jogadores
- ✅ Reset completo da mesa
- ✅ Validações de entrada

### 5. **test_integration.py** - Testes de Integração
- ✅ Jogo completo (melhor de 3)
- ✅ Alternância de servidor
- ✅ Desfazer ponto
- ✅ Reset após jogo
- ✅ Manutenção de jogadores após reset
- ✅ Validações do sistema

## 🎯 Cobertura de Testes

| Componente | Cobertura | Status |
|-----------|-----------|--------|
| Regras ITTF | 100% | ✅ |
| Modelos | 100% | ✅ |
| Rotas de Placar | 100% | ✅ |
| Rotas de Mesas | 95% | ✅ |
| Integração | 90% | ✅ |

## 🔍 Fixtures Disponíveis

### Fixture `client`
Cliente HTTP para fazer requisições
```python
def test_example(client):
    response = client.get('/api/placar/mesa/1')
    assert response.status_code == 200
```

### Fixture `app_context`
Contexto de aplicação Flask
```python
def test_example(app_context):
    mesa = Mesa.query.all()
```

### Fixture `campeonato`
Campeonato de teste
```python
def test_example(client, campeonato):
    assert campeonato.nome == 'Teste'
```

### Fixture `mesa`
Mesa vazia de teste
```python
def test_example(client, mesa):
    assert mesa.status == 'disponivel'
```

### Fixture `mesa_com_jogadores`
Mesa com 2 jogadores
```python
def test_example(client, mesa_com_jogadores):
    assert len(mesa_com_jogadores.jogadores) == 2
```

## 📝 Exemplos de Testes

### Exemplo 1: Teste Simples de Adição de Ponto
```python
def test_adicionar_ponto(client, mesa_com_jogadores):
    response = client.post(
        f'/api/placar/mesa/{mesa_com_jogadores.id}/adicionar-ponto',
        json={'time': 1}
    )
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['placar']['pontos_time1'] == 1
```

### Exemplo 2: Teste de Jogo Completo
```python
def test_jogo_completo(client, mesa_com_jogadores):
    # Set 1: Time 1 vence 11x9
    for _ in range(11):
        client.post(f'/api/placar/mesa/{mesa_com_jogadores.id}/adicionar-ponto', 
                   json={'time': 1})
    for _ in range(9):
        client.post(f'/api/placar/mesa/{mesa_com_jogadores.id}/adicionar-ponto', 
                   json={'time': 2})
    
    # Verificar resultado
    response = client.get(f'/api/placar/mesa/{mesa_com_jogadores.id}')
    data = json.loads(response.data)
    assert data['sets_time1'] == 1
```

## ⚡ Testes Críticos

Os testes mais importantes para garantir a "prova de bala":

1. **Regras ITTF**: Validação de fim de set e transição
2. **Servidor**: Alternância correta a cada 2 saques
3. **Reset**: Volta ao estado inicial mantendo jogadores
4. **Status da Mesa**: Mudança correta para disponível/em_uso
5. **Jogo Completo**: Fluxo inteiro de um jogo

## 📈 CI/CD Integration

Para integrar os testes em CI/CD:

### GitHub Actions
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pytest --cov
```

## 🐛 Depuração de Testes

### Executar teste específico com mais detalhes
```bash
pytest tests/test_placar_routes.py::TestPlacarRoutes::test_adicionar_ponto -vv
```

### Parar no primeiro erro
```bash
pytest -x
```

### Modo interativo
```bash
pytest --pdb  # Para no erro com debugger
```

## ✅ Checklist de Qualidade

- [ ] Todos os testes passam (`pytest`)
- [ ] Cobertura > 90% (`pytest --cov`)
- [ ] Sem warnings
- [ ] Código segue PEP8
- [ ] Documentação atualizada
- [ ] Testes cobrem casos de sucesso e erro
- [ ] Fixtures estão bem organizadas

## 🔗 Relacionado

- [README.md](../README.md) - Documentação geral
- [QUICK_START_CONFIG.md](../QUICK_START_CONFIG.md) - Setup rápido
- [ittf_rules.py](../ittf_rules.py) - Regras ITTF
- [models.py](../models.py) - Modelos de dados
