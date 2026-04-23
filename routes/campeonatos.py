from flask import Blueprint, request, jsonify
from sqlalchemy.exc import OperationalError
from chaveamento import (
    alocar_partida_em_mesa,
    alocar_partida_grupo_em_mesa,
    avancar_para_mata_mata,
    gerar_chaveamento_vivo,
    gerar_fase_grupos,
    liberar_mesa_para_proxima_partida,
    liberar_mesa_partida_grupo,
    normalizar_categoria,
    obter_chaveamento_serializado,
    obter_estado_torneio,
)
from models import ChaveamentoPartida, PartidaGrupo, db, Campeonato, Mesa, Placar, JogadorInscrito

bp = Blueprint('campeonatos', __name__, url_prefix='/api/campeonatos')


def normalizar_nivel(valor):
    nivel = (valor or 'iniciante').strip().lower()
    niveis_validos = {'iniciante', 'intermediario', 'avancado'}
    return nivel if nivel in niveis_validos else 'iniciante'


@bp.route('', methods=['GET'])
def listar_campeonatos():
    """Lista todos os campeonatos"""
    campeonatos = Campeonato.query.all()
    return jsonify([c.to_dict() for c in campeonatos])

@bp.route('', methods=['POST'])
def criar_campeonato():
    """Cria um novo campeonato"""
    dados = request.get_json()
    
    if not dados or 'nome' not in dados:
        return jsonify({'erro': 'Nome do campeonato é obrigatório'}), 400
    
    def _salvar_campeonato():
        novo = Campeonato(
            nome=dados['nome'],
            descricao=dados.get('descricao', '')
        )
        db.session.add(novo)
        db.session.commit()
        return novo

    try:
        novo_campeonato = _salvar_campeonato()
        return jsonify(novo_campeonato.to_dict()), 201
    except OperationalError:
        db.session.rollback()
        # Recupera schema em runtime e tenta novamente.
        db.create_all()
        novo_campeonato = _salvar_campeonato()
        return jsonify(novo_campeonato.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:id>', methods=['GET'])
def obter_campeonato(id):
    """Obtém um campeonato específico"""
    campeonato = Campeonato.query.get(id)
    
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404
    
    return jsonify(campeonato.to_dict())

@bp.route('/<int:id>', methods=['PUT'])
def atualizar_campeonato(id):
    """Atualiza um campeonato"""
    campeonato = Campeonato.query.get(id)
    
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404
    
    dados = request.get_json()
    
    if 'nome' in dados:
        campeonato.nome = dados['nome']
    if 'descricao' in dados:
        campeonato.descricao = dados['descricao']
    if 'status' in dados:
        campeonato.status = dados['status']
    
    try:
        db.session.commit()
        return jsonify(campeonato.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:id>', methods=['DELETE'])
def deletar_campeonato(id):
    """Deleta um campeonato e suas mesas"""
    campeonato = Campeonato.query.get(id)
    
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404
    
    try:
        db.session.delete(campeonato)
        db.session.commit()
        return jsonify({'mensagem': 'Campeonato deletado com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:id>/mesas', methods=['GET'])
def listar_mesas_campeonato(id):
    """Lista todas as mesas de um campeonato"""
    campeonato = Campeonato.query.get(id)
    
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404
    
    return jsonify([m.to_dict() for m in campeonato.mesas])

@bp.route('/<int:id>/jogadores-inscritos', methods=['GET'])
def listar_jogadores_inscritos(id):
    """Lista todos os jogadores inscritos em um campeonato"""
    campeonato = Campeonato.query.get(id)
    
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404
    
    jogadores = JogadorInscrito.query.filter_by(campeonato_id=id, ativo=True).all()
    return jsonify([j.to_dict() for j in jogadores])


@bp.route('/<int:id>/chaveamento', methods=['GET'])
def obter_chaveamento(id):
    """Obtém o chaveamento do campeonato, em modo simulado ou vivo."""
    campeonato = Campeonato.query.get(id)

    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404

    chaveamento = obter_chaveamento_serializado(id)
    chaveamento['campeonato_nome'] = campeonato.nome
    return jsonify(chaveamento)


@bp.route('/<int:id>/chaveamento-vivo', methods=['POST'])
def criar_chaveamento_vivo(id):
    """Gera ou regenera o chaveamento vivo do campeonato."""
    campeonato = Campeonato.query.get(id)

    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404

    dados = request.get_json(force=True, silent=True) or {}
    force = dados.get('force', False)

    if not force:
        partida_ativa = ChaveamentoPartida.query.filter(
            ChaveamentoPartida.campeonato_id == id,
            ChaveamentoPartida.status.in_(['em_andamento', 'finalizada'])
        ).first()
        if partida_ativa:
            return jsonify({
                'erro': 'Existem partidas em andamento ou finalizadas. Confirme para regenerar.',
                'requer_confirmacao': True
            }), 409

    try:
        chaveamento = gerar_chaveamento_vivo(id)
        db.session.commit()

        try:
            from app import broadcast_campeonato_update
            broadcast_campeonato_update(id, 'chaveamento_atualizado')
        except Exception as e:
            print(f"[BROADCAST ERROR] Erro ao notificar chaveamento: {e}")

        chaveamento['campeonato_nome'] = campeonato.nome
        return jsonify(chaveamento), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400


@bp.route('/<int:id>/chaveamento/partidas/<int:partida_id>/alocar-mesa', methods=['POST'])
def alocar_partida_chaveamento(id, partida_id):
    """Vincula uma partida do chaveamento a uma mesa e prepara os jogadores."""
    campeonato = Campeonato.query.get(id)

    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404

    dados = request.get_json() or {}
    mesa_id = dados.get('mesa_id')
    if not mesa_id:
        return jsonify({'erro': 'mesa_id é obrigatório'}), 400

    try:
        partida = alocar_partida_em_mesa(id, partida_id, int(mesa_id))
        db.session.commit()

        try:
            from app import broadcast_campeonato_update
            broadcast_campeonato_update(id, 'chaveamento_atualizado')
        except Exception as e:
            print(f"[BROADCAST ERROR] Erro ao notificar alocação de partida: {e}")

        return jsonify({
            'mensagem': 'Partida alocada à mesa com sucesso',
            'partida': partida.to_dict()
        })
    except ValueError as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400


@bp.route('/<int:id>/chaveamento/partidas/<int:partida_id>/liberar-mesa', methods=['POST'])
def liberar_mesa_partida_chaveamento(id, partida_id):
    """Desvincula a mesa de uma partida finalizada e a aloca na próxima partida pronta, se houver."""
    campeonato = Campeonato.query.get(id)

    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404

    try:
        proxima = liberar_mesa_para_proxima_partida(id, partida_id)
        db.session.commit()

        try:
            from app import broadcast_campeonato_update
            broadcast_campeonato_update(id, 'chaveamento_atualizado')
        except Exception as e:
            print(f"[BROADCAST ERROR] Erro ao notificar liberação de mesa: {e}")

        return jsonify({
            'mensagem': 'Mesa liberada com sucesso',
            'proxima_partida': proxima.to_dict() if proxima else None
        })
    except ValueError as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400


@bp.route('/<int:id>/torneio', methods=['GET'])
def obter_torneio(id):
    """Retorna o estado completo do torneio (fase de grupos + mata-mata)."""
    campeonato = Campeonato.query.get(id)
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404

    torneio = obter_estado_torneio(id)
    torneio['campeonato_nome'] = campeonato.nome
    return jsonify(torneio)


@bp.route('/<int:id>/fase-grupos', methods=['POST'])
def criar_fase_grupos(id):
    """Gera a fase de grupos para o campeonato."""
    campeonato = Campeonato.query.get(id)
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404

    dados = request.get_json(force=True, silent=True) or {}
    jogadores_por_grupo = int(dados.get('jogadores_por_grupo', 4))

    try:
        torneio = gerar_fase_grupos(id, jogadores_por_grupo=jogadores_por_grupo)
        db.session.commit()

        try:
            from app import broadcast_campeonato_update
            broadcast_campeonato_update(id, 'chaveamento_atualizado')
        except Exception as e:
            print(f"[BROADCAST ERROR] {e}")

        torneio['campeonato_nome'] = campeonato.nome
        return jsonify(torneio), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400


@bp.route('/<int:id>/grupos/partidas/<int:partida_id>/alocar-mesa', methods=['POST'])
def alocar_partida_grupo(id, partida_id):
    """Aloca uma partida de grupo em uma mesa."""
    campeonato = Campeonato.query.get(id)
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404

    dados = request.get_json() or {}
    mesa_id = dados.get('mesa_id')
    if not mesa_id:
        return jsonify({'erro': 'mesa_id é obrigatório'}), 400

    try:
        partida = alocar_partida_grupo_em_mesa(id, partida_id, int(mesa_id))
        db.session.commit()

        try:
            from app import broadcast_campeonato_update
            broadcast_campeonato_update(id, 'chaveamento_atualizado')
        except Exception as e:
            print(f"[BROADCAST ERROR] {e}")

        return jsonify({'mensagem': 'Partida alocada com sucesso', 'partida': partida.to_dict()})
    except ValueError as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400


@bp.route('/<int:id>/grupos/partidas/<int:partida_id>/liberar-mesa', methods=['POST'])
def liberar_mesa_grupo(id, partida_id):
    """Libera a mesa de uma partida de grupo finalizada."""
    campeonato = Campeonato.query.get(id)
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404

    try:
        liberar_mesa_partida_grupo(id, partida_id)
        db.session.commit()

        try:
            from app import broadcast_campeonato_update
            broadcast_campeonato_update(id, 'chaveamento_atualizado')
        except Exception as e:
            print(f"[BROADCAST ERROR] {e}")

        return jsonify({'mensagem': 'Mesa liberada com sucesso'})
    except ValueError as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400


@bp.route('/<int:id>/avancar-mata-mata', methods=['POST'])
def avancar_mata_mata(id):
    """Gera o chaveamento eliminatório com os classificados dos grupos."""
    campeonato = Campeonato.query.get(id)
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404

    dados = request.get_json(force=True, silent=True) or {}
    qtd_avancam = int(dados.get('qtd_avancam', 2))

    try:
        torneio = avancar_para_mata_mata(id, qtd_avancam=qtd_avancam)
        db.session.commit()

        try:
            from app import broadcast_campeonato_update
            broadcast_campeonato_update(id, 'chaveamento_atualizado')
        except Exception as e:
            print(f"[BROADCAST ERROR] {e}")

        torneio['campeonato_nome'] = campeonato.nome
        return jsonify(torneio)
    except ValueError as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400


@bp.route('/<int:id>/jogadores-inscritos', methods=['POST'])
def adicionar_jogador_inscrito(id):
    """Adiciona um novo jogador ao campeonato"""
    campeonato = Campeonato.query.get(id)
    
    if not campeonato:
        return jsonify({'erro': 'Campeonato não encontrado'}), 404
    
    dados = request.get_json()
    
    if not dados or 'nome' not in dados:
        return jsonify({'erro': 'Nome do jogador é obrigatório'}), 400
    
    try:
        novo_jogador = JogadorInscrito(
            nome=dados['nome'],
            categoria=normalizar_categoria(dados.get('categoria')),
            nivel=normalizar_nivel(dados.get('nivel')),
            campeonato_id=id,
            ativo=True
        )
        db.session.add(novo_jogador)
        db.session.commit()
        
        return jsonify(novo_jogador.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:id>/jogadores-inscritos/<int:jogador_id>', methods=['DELETE'])
def remover_jogador_inscrito(id, jogador_id):
    """Remove um jogador inscrito do campeonato"""
    jogador = JogadorInscrito.query.get(jogador_id)
    
    if not jogador or jogador.campeonato_id != id:
        return jsonify({'erro': 'Jogador não encontrado'}), 404
    
    try:
        # Marcar como inativo ao invés de deletar
        jogador.ativo = False
        db.session.commit()
        
        return jsonify({'mensagem': 'Jogador removido com sucesso'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/<int:id>/jogadores-inscritos/<int:jogador_id>', methods=['PUT'])
def atualizar_jogador_inscrito(id, jogador_id):
    """Atualiza um jogador inscrito"""
    jogador = JogadorInscrito.query.get(jogador_id)
    
    if not jogador or jogador.campeonato_id != id:
        return jsonify({'erro': 'Jogador não encontrado'}), 404
    
    dados = request.get_json()
    
    if 'nome' in dados:
        jogador.nome = dados['nome']
    if 'categoria' in dados:
        jogador.categoria = normalizar_categoria(dados.get('categoria'))
    if 'nivel' in dados:
        jogador.nivel = normalizar_nivel(dados.get('nivel'))
    if 'ativo' in dados:
        jogador.ativo = dados['ativo']
    
    try:
        db.session.commit()
        return jsonify(jogador.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400
