from flask import Blueprint, request, jsonify, current_app
from models import db, Mesa, Campeonato, Placar

bp = Blueprint('mesas', __name__, url_prefix='/api/mesas')

@bp.route('', methods=['POST'])
def criar_mesa():
    """Cria uma nova mesa em um campeonato"""
    dados = request.get_json()
    
    if not dados or 'campeonato_id' not in dados or 'numero' not in dados:
        return jsonify({'erro': 'campeonato_id e numero são obrigatórios'}), 400
    
    campeonato = Campeonato.query.get(dados['campeonato_id'])
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404
    
    # Verificar se já existe mesa com mesmo número neste campeonato
    mesa_existente = Mesa.query.filter_by(
        campeonato_id=dados['campeonato_id'],
        numero=dados['numero']
    ).first()
    
    if mesa_existente:
        return jsonify({'erro': f'Já existe uma mesa com o número {dados["numero"]} neste campeonato'}), 409
    
    try:
        nova_mesa = Mesa(
            numero=dados['numero'],
            campeonato_id=dados['campeonato_id']
        )
        db.session.add(nova_mesa)
        db.session.flush()
        
        # Criar placar para a mesa (necessário para o sistema de placar)
        try:
            placar_existente = Placar.query.filter_by(mesa_id=nova_mesa.id).first()
            if not placar_existente:
                placar = Placar(mesa_id=nova_mesa.id)
                db.session.add(placar)
        except Exception:
            pass
        
        db.session.commit()
        
        return jsonify(nova_mesa.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:id>', methods=['GET'])
def obter_mesa(id):
    """Obtém uma mesa específica"""
    mesa = Mesa.query.get(id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    return jsonify(mesa.to_dict())

@bp.route('/<int:id>', methods=['PUT'])
def atualizar_mesa(id):
    """Atualiza status da mesa"""
    mesa = Mesa.query.get(id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    dados = request.get_json()
    
    if 'status' in dados:
        mesa.status = dados['status']
    
    try:
        db.session.commit()
        return jsonify(mesa.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:id>', methods=['DELETE'])
def deletar_mesa(id):
    """Deleta uma mesa"""
    mesa = Mesa.query.get(id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    try:
        db.session.delete(mesa)
        db.session.commit()
        return jsonify({'mensagem': 'Mesa deletada com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:id>/resetar', methods=['POST'])
def resetar_mesa(id):
    """
    Reseta completamente a mesa para começar um novo jogo.
    Reseta todos os dados: pontos, sets, servidor, saques e sets vencidos dos jogadores.
    """
    mesa = Mesa.query.get(id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404
    
    try:
        # Resetar placar e sets
        mesa.placar.pontos_time1 = 0
        mesa.placar.pontos_time2 = 0
        mesa.placar.set_numero = 1
        mesa.placar.sets_time1 = 0
        mesa.placar.sets_time2 = 0
        mesa.placar.servidor_time = mesa.placar.servidor_inicial_jogo
        mesa.placar.serves_no_set = 0
        mesa.placar.lados_invertidos = False
        mesa.placar.status = 'em_andamento'
        
        # Resetar status da mesa
        mesa.status = 'em_uso'
        
        # Resetar estatísticas por vínculo de mesa
        for jogador_mesa in mesa.jogadores_mesa:
            jogador_mesa.sets_vencidos = 0
            jogador_mesa.pontos_marcados = 0
            print(f"[RESET] Jogador {jogador_mesa.jogador.nome} - stats resetadas para 0")
        
        db.session.commit()
        
        print(f"[JOGO RESETADO] Mesa {id} pronta para novo jogo!")
        
        return jsonify(mesa.placar.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:id>/atualizar-jogadores', methods=['POST'])
def atualizar_jogadores(id):
    """
    Atualiza os nomes dos jogadores de um time
    Espera: { "time": 1 ou 2, "nomes": ["Jogador 1", "Jogador 2"] }
    """
    mesa = Mesa.query.get(id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada', 'sucesso': False}), 404
    
    try:
        dados = request.get_json()
        time = dados.get('time')
        nomes = dados.get('nomes', [])
        
        if not time or not nomes:
            return jsonify({'erro': 'time e nomes são obrigatórios', 'sucesso': False}), 400
        
        if time not in [1, 2]:
            return jsonify({'erro': 'time deve ser 1 ou 2', 'sucesso': False}), 400
        
        # Obter vínculos de jogadores do time na mesa
        jogadores_mesa = [jm for jm in mesa.jogadores_mesa if jm.time == time]
        
        # Atualizar nomes dos jogadores existentes
        for i, nome in enumerate(nomes):
            if i < len(jogadores_mesa):
                jogadores_mesa[i].jogador.nome = nome.strip()

        # Se o time tinha mais jogadores do que a nova lista, remove os excedentes da mesa
        if len(jogadores_mesa) > len(nomes):
            for jogador_mesa in jogadores_mesa[len(nomes):]:
                db.session.delete(jogador_mesa)
        
        # Mudar status da mesa para 'em_uso' quando há jogadores
        mesa.status = 'em_uso'
        
        db.session.commit()
        
        print(f"[JOGADORES ATUALIZADOS] Mesa {id}, Time {time}: {', '.join(nomes)}")
        
        # Notificar via Socket.io que os jogadores foram atualizados
        try:
            from app import broadcast_jogadores_update, broadcast_placar_update
            print(f"[BROADCAST] Enviando notificação de atualização de jogadores para mesa {id}")
            broadcast_jogadores_update(id, mesa.campeonato_id)
            broadcast_placar_update(id, mesa.placar.to_dict())
        except Exception as e:
            print(f"[ERRO NO BROADCAST] {str(e)}")
        
        return jsonify({'sucesso': True, 'mensagem': 'Jogadores atualizados com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e), 'sucesso': False}), 400


@bp.route('/<int:id>/atualizar-placar', methods=['POST'])
def atualizar_placar(id):
    """Força o refresh do placar e jogadores para clientes inscritos na mesa."""
    mesa = Mesa.query.get(id)

    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada', 'sucesso': False}), 404

    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado', 'sucesso': False}), 404

    try:
        from app import broadcast_jogadores_update, broadcast_placar_update

        broadcast_jogadores_update(mesa.id, mesa.campeonato_id)
        broadcast_placar_update(mesa.id, mesa.placar.to_dict())

        return jsonify({
            'sucesso': True,
            'mensagem': 'Atualização enviada com sucesso',
            'mesa': mesa.to_dict(),
            'placar': mesa.placar.to_dict()
        })
    except Exception as e:
        current_app.logger.exception('Erro ao forçar atualização do placar')
        return jsonify({'erro': str(e), 'sucesso': False}), 500
