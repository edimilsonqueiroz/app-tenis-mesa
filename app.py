from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from dotenv import load_dotenv
import os
from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

# Load environment variables from .env file
load_dotenv()

from config import config
from models import db
from routes import register_blueprints

app = Flask(__name__)
app.config.from_object(config)

# Inicializar extensões
db.init_app(app)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Registrar blueprints das rotas da API
register_blueprints(app)


def _garantir_coluna_nivel_jogador_inscrito():
    """Migração leve para adicionar coluna `nivel` em bases existentes."""
    inspector = inspect(db.engine)
    tabelas = inspector.get_table_names()
    if 'jogadores_inscritos' not in tabelas:
        return

    colunas = [c['name'] for c in inspector.get_columns('jogadores_inscritos')]
    if 'nivel' in colunas:
        return

    with db.engine.begin() as connection:
        connection.execute(text(
            "ALTER TABLE jogadores_inscritos "
            "ADD COLUMN nivel VARCHAR(20) DEFAULT 'iniciante'"
        ))


# Criar tabelas do banco de dados
with app.app_context():
    db.create_all()
    _garantir_coluna_nivel_jogador_inscrito()


@app.before_request
def garantir_schema_em_runtime():
    """Auto-recupera schema se o banco for recriado com o servidor em execução."""
    try:
        inspector = inspect(db.engine)
        tabelas_existentes = set(inspector.get_table_names())
        tabelas_esperadas = set(db.metadata.tables.keys())
        faltantes = tabelas_esperadas - tabelas_existentes

        if faltantes:
            db.create_all()
            _garantir_coluna_nivel_jogador_inscrito()
    except OperationalError:
        db.session.rollback()
        try:
            db.create_all()
            _garantir_coluna_nivel_jogador_inscrito()
        except Exception as e:
            print(f"[SCHEMA RECOVERY ERROR] {e}")
    except Exception as e:
        print(f"[SCHEMA CHECK ERROR] {e}")

# ==================== ROTAS WEB ====================

@app.route('/')
def index():
    """Página inicial - Dashboard principal"""
    return render_template('index.html')

@app.route('/placar/<int:campeonato_id>')
def placar(campeonato_id):
    """Página de placar para TV/Desktop - mostra todas as mesas de um campeonato"""
    return render_template('placar.html', campeonato_id=campeonato_id)

@app.route('/placar-mesa/<int:mesa_id>')
def placar_mesa(mesa_id):
    """Página de placar para uma mesa específica"""
    from models import Mesa
    from flask import request, redirect, url_for
    
    mesa = Mesa.query.get(mesa_id)
    
    # Verificar se a mesa existe
    if not mesa:
        return redirect(url_for('index'))
    
    # Verificar se existem jogadores na mesa
    if not mesa.jogadores or len(mesa.jogadores) == 0:
        return redirect(url_for('gerenciar_campeonato', campeonato_id=mesa.campeonato_id))
    
    # Tenta obter campeonato_id do query parameter ou do banco de dados
    campeonato_id = request.args.get('campeonato_id')
    if not campeonato_id and mesa:
        campeonato_id = mesa.campeonato_id
    
    return render_template('placar_mesa.html', mesa_id=mesa_id, campeonato_id=campeonato_id)

@app.route('/controle/<int:mesa_id>')
def controle(mesa_id):
    """Controle remoto para celular - controla uma mesa específica"""
    from models import Mesa
    from flask import redirect, url_for
    
    mesa = Mesa.query.get(mesa_id)
    
    # Verificar se a mesa existe
    if not mesa:
        return redirect(url_for('index'))
    
    # Verificar se existem jogadores na mesa
    if not mesa.jogadores or len(mesa.jogadores) == 0:
        return redirect(url_for('gerenciar_campeonato', campeonato_id=mesa.campeonato_id))
    
    return render_template('controle.html', mesa_id=mesa_id)

@app.route('/criar-campeonato')
def criar_campeonato():
    """Página para criar novo campeonato"""
    return render_template('criar_campeonato.html')

@app.route('/campeonato/<int:campeonato_id>')
def gerenciar_campeonato(campeonato_id):
    """Página principal do campeonato (somente mesas)"""
    return render_template('gerenciar_campeonato.html', campeonato_id=campeonato_id, modo_pagina='mesas')


@app.route('/campeonato/<int:campeonato_id>/jogadores')
def gerenciar_campeonato_jogadores(campeonato_id):
    """Página de cadastro e gerenciamento de jogadores"""
    return render_template('gerenciar_campeonato.html', campeonato_id=campeonato_id, modo_pagina='jogadores')


@app.route('/campeonato/<int:campeonato_id>/chaveamento')
def gerenciar_campeonato_chaveamento(campeonato_id):
    """Página de fase de grupos e chaveamento"""
    return render_template('gerenciar_campeonato.html', campeonato_id=campeonato_id, modo_pagina='chaveamento')

@app.route('/ranking')
def ranking():
    """Página de ranking geral dos jogadores"""
    return render_template('ranking.html')

# ==================== WEBSOCKETS ====================

@socketio.on('connect')
def handle_connect():
    """Usuário se conectou"""
    print(f'Cliente conectado: {request.sid}')
    emit('resposta', {'dados': 'Conectado ao servidor de placar'})

@socketio.on('disconnect')
def handle_disconnect():
    """Usuário se desconectou"""
    print(f'Cliente desconectado: {request.sid}')

@socketio.on('inscrever_mesa')
def handle_inscrever_mesa(data):
    """Inscreve um cliente para receber atualizações de uma mesa"""
    mesa_id = data.get('mesa_id')
    room = f'mesa_{mesa_id}'
    print(f"[INSCRIÇÃO] Cliente {request.sid} inscrevendo na sala: {room}")
    join_room(room)
    print(f"[INSCRIÇÃO] Cliente {request.sid} inscrito com sucesso na sala: {room}")
    emit('resposta', {'mensagem': f'Inscrito na mesa {mesa_id}'})

@socketio.on('desinscrever_mesa')
def handle_desinscrever_mesa(data):
    """Desinscreve um cliente das atualizações de uma mesa"""
    mesa_id = data.get('mesa_id')
    room = f'mesa_{mesa_id}'
    leave_room(room)
    emit('resposta', {'mensagem': f'Desinscrito da mesa {mesa_id}'})

@socketio.on('inscrever_campeonato')
def handle_inscrever_campeonato(data):
    """Inscreve um cliente para receber atualizações de um campeonato"""
    campeonato_id = data.get('campeonato_id')
    room = f'campeonato_{campeonato_id}'
    join_room(room)
    emit('resposta', {'mensagem': f'Inscrito no campeonato {campeonato_id}'})

@socketio.on('desinscrever_campeonato')
def handle_desinscrever_campeonato(data):
    """Desinscreve um cliente das atualizações de um campeonato"""
    campeonato_id = data.get('campeonato_id')
    room = f'campeonato_{campeonato_id}'
    leave_room(room)
    emit('resposta', {'mensagem': f'Desinscrito do campeonato {campeonato_id}'})

@socketio.on('controle_aberto')
def handle_controle_aberto(data):
    """
    Notifica quando alguém abre o controle remoto de uma mesa
    (via QR code ou link direto)
    """
    mesa_id = data.get('mesa_id')
    if mesa_id:
        from models import Mesa
        mesa = Mesa.query.get(mesa_id)
        
        if mesa:
            # Notifica para a sala da mesa que o controle foi aberto
            emit('controle_conectado', {'mesa_id': mesa_id}, room=f'mesa_{mesa_id}')
            
            # Notifica para a sala do campeonato (para fechar modal em gerenciar_campeonato.html)
            emit('controle_conectado', {'mesa_id': mesa_id}, room=f'campeonato_{mesa.campeonato_id}')
            
            print(f'[CONTROLE ABERTO] Mesa {mesa_id} - Campeonato {mesa.campeonato_id} - Sessão: {request.sid}')

# ==================== BROADCASTING ====================

def broadcast_placar_update(mesa_id, placar_data):
    """Envia atualização de placar para todos os clientes inscritos na mesa"""
    room = f'mesa_{mesa_id}'
    socketio.emit('placar_atualizado', {
        'mesa_id': mesa_id,
        'placar': placar_data
    }, room=room)

def broadcast_campeonato_update(campeonato_id, tipo='mesas_atualizadas'):
    """Envia atualização de campeonato para todos os clientes inscritos"""
    room = f'campeonato_{campeonato_id}'
    socketio.emit(tipo, {
        'campeonato_id': campeonato_id,
        'timestamp': str(__import__('datetime').datetime.utcnow())
    }, room=room)

def broadcast_jogadores_update(mesa_id, campeonato_id=None):
    """Envia notificação de atualização de jogadores para todos os clientes da mesa"""
    from models import Mesa
    
    # Buscar dados atualizados da mesa
    mesa = Mesa.query.get(mesa_id)
    
    # Emitir para a sala da mesa
    room_mesa = f'mesa_{mesa_id}'
    print(f"[BROADCAST_JOGADORES] Emitindo evento para sala: {room_mesa}")
    socketio.emit('jogadores_atualizados', {
        'mesa_id': mesa_id,
        'mesa': mesa.to_dict() if mesa else None,
        'timestamp': str(__import__('datetime').datetime.utcnow())
    }, room=room_mesa)
    print(f"[BROADCAST_JOGADORES] Evento enviado para sala: {room_mesa}")
    
    # Se houver campeonato_id, também emitir para a sala do campeonato
    if campeonato_id:
        room_campeonato = f'campeonato_{campeonato_id}'
        print(f"[BROADCAST_JOGADORES] Emitindo evento para sala: {room_campeonato}")
        socketio.emit('jogadores_atualizados', {
            'mesa_id': mesa_id,
            'campeonato_id': campeonato_id,
            'mesa': mesa.to_dict() if mesa else None,
            'timestamp': str(__import__('datetime').datetime.utcnow())
        }, room=room_campeonato)
        print(f"[BROADCAST_JOGADORES] Evento enviado para sala: {room_campeonato}")

# ==================== Hooks para Broadcasting ====================
# Esses hooks atualizam os clientes websocket quando há mudanças na API

from models import Placar, Mesa, Campeonato

@db.event.listens_for(Placar, 'after_update')
def receive_after_update_placar(mapper, connection, target):
    """Dispara quando um placar é atualizado"""
    if target.mesa:
        broadcast_placar_update(target.mesa_id, target.to_dict())
        broadcast_campeonato_update(target.mesa.campeonato_id, 'placar_atualizado')

@db.event.listens_for(Mesa, 'after_insert')
def receive_after_insert_mesa(mapper, connection, target):
    """Dispara quando uma mesa é criada"""
    broadcast_campeonato_update(target.campeonato_id, 'mesa_criada')

@db.event.listens_for(Mesa, 'after_delete')
def receive_after_delete_mesa(mapper, connection, target):
    """Dispara quando uma mesa é deletada"""
    broadcast_campeonato_update(target.campeonato_id, 'mesa_deletada')

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
