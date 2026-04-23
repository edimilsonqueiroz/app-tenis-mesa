# Placar de Tênis de Mesa

Uma aplicação web completa para gerenciar placares de tênis de mesa em campeonatos, com suporte a múltiplas mesas e controle remoto via celular.

## 🎯 Funcionalidades

- **Gerenciamento de Campeonatos**: Criar, visualizar e deletar campeonatos
- **Gerenciamento de Mesas**: Adicionar múltiplas mesas por campeonato
- **Jogadores**: Adicionar/remover jogadores nas mesas com atribuição automática de times
- **Placar em Tempo Real**: Sincronização instantânea entre desktop/TV e celular
- **Controle Remoto**: Interface mobile responsiva para alterar pontuação
- **Exibição em TV**: Placar grande para visualização em TV ou monitor
- **WebSockets**: Sincronização em tempo real para todos os clientes conectados

## 🚀 Instalação

### Pré-requisitos

- Python 3.8 ou superior
- pip (gerenciador de pacotes Python)

### Setup

1. **Clone ou baixe o projeto**
```bash
cd app-tenis-mesa
```

2. **Crie um ambiente virtual** (opcional, mas recomendado)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Instale as dependências**
```bash
pip install -r requirements.txt
```

## ⚙️ Configuração por Ambiente

### Desenvolvimento (SQLite) - Padrão
```bash
# Sem fazer nada, SQLite será usado automaticamente
python app.py
# Banco criado automaticamente em instance/tenis_mesa.db
```

### Produção (PostgreSQL)

1. **Crie um arquivo `.env`** (use `.env.example` como referência)
```bash
ENVIRONMENT=production
SECRET_KEY=seu-secret-key-super-seguro-aqui
DB_USER=postgres
DB_PASSWORD=sua-senha-postgres
DB_HOST=seu-host-postgres
DB_PORT=5432
DB_NAME=tenis_mesa
```

2. **Rode a aplicação**
```bash
python app.py
# Agora usa PostgreSQL automaticamente!
```

Para mais detalhes, veja [PRODUCTION_SETUP.md](PRODUCTION_SETUP.md) ou [QUICK_START_CONFIG.md](QUICK_START_CONFIG.md).

4. **Execute a aplicação**
```bash
python app.py
```

A aplicação estará disponível em `http://localhost:5000`

## 📱 Como Usar

### 1. Criar um Campeonato

1. Acesse `http://localhost:5000`
2. Clique em "➕ Novo Campeonato"
3. Digite o nome e descrição (opcional)
4. Clique em "Criar Campeonato"

### 2. Adicionar Mesas

1. Clique em "Gerenciar" no campeonato desejado
2. Digite o número da mesa no campo "Adicionar Nova Mesa"
3. Clique em "Criar Mesa"
4. Repita para adicionar quantas mesas desejar

### 3. Adicionar Jogadores

1. Na página de gerenciamento do campeonato, praticamente cada mesa tem um campo para adicionar jogadores
2. Digite o nome do jogador
3. Selecione o time (Time 1 ou Time 2)
4. Clique em "+"
5. Repita para adicionar todos os jogadores

### 4. Visualizar Placar em TV/Desktop

1. Clique em "Ver Placar" no campeonato (na página inicial)
2. Uma página com todas as mesas será exibida
3. Clique em "Abrir Controle Remoto" para abrir o controlador em outra aba

### 5. Usar o Controle Remoto

1. Acesse o controle remoto em `http://localhost:5000/controle/<mesa_id>`
2. Ou clique em "Abrir Controle Remoto" na página de placar
3. Use os botões **+** para adicionar pontos
4. Use os botões **−** para remover pontos
5. Clique em "[↻ Reset]" para zerar o placar
6. Clique em "[✕ Sair]" para fechar

## [⚙️] Estrutura do Projeto

```
app-tenis-mesa/
├── app.py                  # Aplicação principal Flask
├── config.py               # Configurações
├── models.py               # Modelos de banco de dados
├── requirements.txt        # Dependências Python
├── routes/                 # Endpoints da API
│   ├── __init__.py
│   ├── campeonatos.py      # API de campeonatos
│   ├── mesas.py            # API de mesas
│   ├── jogadores.py        # API de jogadores
│   └── placar.py           # API de placar
├── templates/              # Templates HTML
│   ├── index.html          # Dashboard principal
│   ├── placar.html         # Exibição para TV
│   ├── controle.html       # Controle remoto
│   └── gerenciar_campeonato.html  # Gerenciamento
└── static/                 # Arquivos estáticos
    └── css/
        ├── style.css       # Estilos principais
        └── mobile.css      # Estilos para mobile
```

## 🔌 Endpoints da API

### Campeonatos
- `GET /api/campeonatos` - Lista todos os campeonatos
- `POST /api/campeonatos` - Cria novo campeonato
- `GET /api/campeonatos/<id>` - Obtém detalhes do campeonato
- `PUT /api/campeonatos/<id>` - Atualiza campeonato
- `DELETE /api/campeonatos/<id>` - Deleta campeonato
- `GET /api/campeonatos/<id>/mesas` - Lista mesas do campeonato

### Mesas
- `POST /api/mesas` - Cria nova mesa
- `GET /api/mesas/<id>` - Obtém detalhes da mesa
- `PUT /api/mesas/<id>` - Atualiza mesa
- `DELETE /api/mesas/<id>` - Deleta mesa
- `POST /api/mesas/<id>/resetar` - Reseta placar

### Jogadores
- `POST /api/jogadores` - Adiciona jogador à mesa
- `GET /api/jogadores/<id>` - Obtém detalhes do jogador
- `PUT /api/jogadores/<id>` - Atualiza jogador
- `DELETE /api/jogadores/<id>` - Remove jogador
- `GET /api/jogadores/mesa/<mesa_id>` - Lista jogadores da mesa

### Placar
- `GET /api/placar/mesa/<mesa_id>` - Obtém placar
- `POST /api/placar/mesa/<mesa_id>/adicionar-ponto` - Adiciona ponto
- `POST /api/placar/mesa/<mesa_id>/remover-ponto` - Remove ponto
- `POST /api/placar/mesa/<mesa_id>/set-pontos` - Define pontos
- `POST /api/placar/mesa/<mesa_id>/status` - Atualiza status

## 🌐 Acesso Remoto

Para acessar a aplicação de outros dispositivos na rede:

1. Descobrir o IP da máquina:
   - **Windows**: `ipconfig` (procure por "IPv4 Address")
   - **macOS/Linux**: `ifconfig` ou `ip addr`

2. Acessar via navegador:
   ```
   http://<SEU_IP>:5000
   ```

3. No celular/tablet, você pode:
   - Acessar diretamente `http://<SEU_IP>:5000/controle/<mesa_id>`
   - Ou escanear um QR code gerado pela aplicação (funcionalidade futura)

## 🛠️ Tecnologias Usadas

- **Flask**: Framework web Python
- **Flask-SocketIO**: WebSockets para sincronização em tempo real
- **SQLAlchemy**: ORM para banco de dados
- **SQLite**: Banco de dados leve e portável
- **HTML5/CSS3**: Frontend responsivo
- **JavaScript**: Interatividade e WebSockets

## 📝 Notas Importantes

1. O banco de dados SQLite é criado automaticamente na primeira execução
2. A aplicação usa WebSockets para sincronização em tempo real
3. Recomenda-se usar em navegadores modernos (Chrome, Firefox, Safari, Edge)
4. Para produção, configure um servidor WSGI adequado (Gunicorn, uWSGI, etc.)

## 🐛 Resolução de Problemas

### Porta 5000 já em uso
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux
lsof -i :5000
kill -9 <PID>
```

### Erro de módulos não encontrados
```bash
pip install -r requirements.txt
```

### Banco de dados corrompido
```bash
# Deletar o arquivo do banco
rm tenis_mesa.db

# Reiniciar a aplicação
python app.py
```

## 📄 Licença

Este projeto é de código aberto e livre para uso.

## 👨‍💻 Autor

Desenvolvido como solução para gerenciamento de campeonatos de tênis de mesa com controle remoto via celular.

---

**Dúvidas?** Verifique se a aplicação está rodando em `http://localhost:5000`
