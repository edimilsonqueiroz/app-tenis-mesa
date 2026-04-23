from flask import Blueprint, request, jsonify
from models import db, Jogador, Mesa

bp = Blueprint('jogadores', __name__, url_prefix='/api/jogadores')

@bp.route('', methods=['POST'])
def adicionar_jogador():
    """Adiciona um jogador a uma mesa"""
    dados = request.get_json()
    
    if not dados or 'mesa_id' not in dados or 'nome' not in dados:
        return jsonify({'erro': 'mesa_id e nome são obrigatórios'}), 400
    
    mesa = Mesa.query.get(dados['mesa_id'])
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    # Validar limite de jogadores (máximo 4 por mesa - 2 de cada time)
    if len(mesa.jogadores) >= 4:
        return jsonify({'erro': 'Mesa já tem o número máximo de jogadores'}), 400
    
    # Validar se jogador inscrito já está em alguma mesa
    jogador_inscrito_id = dados.get('jogador_inscrito_id')
    if jogador_inscrito_id:
        jogador_existente = Jogador.query.filter_by(jogador_inscrito_id=jogador_inscrito_id).first()
        if jogador_existente:
            return jsonify({'erro': f'Este jogador já está na Mesa {jogador_existente.mesa.numero}'}), 400
    
    try:
        novo_jogador = Jogador(
            nome=dados['nome'],
            mesa_id=dados['mesa_id'],
            time=dados.get('time', 1),
            jogador_inscrito_id=jogador_inscrito_id
        )
        db.session.add(novo_jogador)
        db.session.commit()
        
        return jsonify(novo_jogador.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:id>', methods=['GET'])
def obter_jogador(id):
    """Obtém um jogador específico"""
    jogador = Jogador.query.get(id)
    
    if not jogador:
        return jsonify({'erro': 'Jogador não encontrado'}), 404
    
    return jsonify(jogador.to_dict())

@bp.route('/<int:id>', methods=['PUT'])
def atualizar_jogador(id):
    """Atualiza informações de um jogador"""
    jogador = Jogador.query.get(id)
    
    if not jogador:
        return jsonify({'erro': 'Jogador não encontrado'}), 404
    
    dados = request.get_json()
    
    if 'nome' in dados:
        jogador.nome = dados['nome']
    if 'time' in dados:
        jogador.time = dados['time']
    
    try:
        db.session.commit()
        return jsonify(jogador.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:id>', methods=['DELETE'])
def deletar_jogador(id):
    """Remove um jogador de uma mesa"""
    jogador = Jogador.query.get(id)
    
    if not jogador:
        return jsonify({'erro': 'Jogador não encontrado'}), 404
    
    try:
        db.session.delete(jogador)
        db.session.commit()
        return jsonify({'mensagem': 'Jogador removido com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/mesa/<int:mesa_id>', methods=['GET'])
def listar_jogadores_mesa(mesa_id):
    """Lista todos os jogadores de uma mesa"""
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    return jsonify([j.to_dict() for j in mesa.jogadores])

@bp.route('/mesa/<int:mesa_id>/estatisticas', methods=['GET'])
def obter_estatisticas_mesa(mesa_id):
    """
    Obtém estatísticas dos jogadores de uma mesa.
    Inclui total de sets vencidos por cada jogador/time.
    """
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    # Agrupar por time
    time1 = [j.to_dict() for j in mesa.jogadores if j.time == 1]
    time2 = [j.to_dict() for j in mesa.jogadores if j.time == 2]
    
    # Calcular total de sets por time
    total_sets_time1 = sum(j['sets_vencidos'] for j in time1)
    total_sets_time2 = sum(j['sets_vencidos'] for j in time2)
    
    return jsonify({
        'mesa_id': mesa_id,
        'time1': {
            'jogadores': time1,
            'total_sets': total_sets_time1
        },
        'time2': {
            'jogadores': time2,
            'total_sets': total_sets_time2
        }
    })
