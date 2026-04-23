from flask import Blueprint, jsonify
from models import db, Jogador, JogadorInscrito, Mesa, Campeonato
from sqlalchemy import func
from sqlalchemy.exc import OperationalError

bp = Blueprint('ranking', __name__, url_prefix='/api/ranking')


@bp.route('', methods=['GET'])
def obter_ranking():
    """
    Retorna o ranking geral dos jogadores com a somatória de pontos e sets vencidos
    em todos os campeonatos que participaram.
    """
    def consultar_ranking():
        # Query: agrupa jogadores por jogador_inscrito_id (ou nome se não tiver vínculo),
        # soma pontos_marcados, sets_vencidos, conta jogos participados
        resultados = (
            db.session.query(
                JogadorInscrito.nome,
                Campeonato.nome.label('campeonato_nome'),
                Campeonato.id.label('campeonato_id'),
                func.sum(Jogador.pontos_marcados).label('total_pontos'),
                func.sum(Jogador.sets_vencidos).label('total_sets'),
                func.count(Jogador.id).label('total_jogos')
            )
            .join(Jogador, Jogador.jogador_inscrito_id == JogadorInscrito.id)
            .join(Campeonato, Campeonato.id == JogadorInscrito.campeonato_id)
            .join(Mesa, Mesa.id == Jogador.mesa_id)
            .group_by(JogadorInscrito.nome, Campeonato.id, Campeonato.nome)
            .all()
        )

        # Agregar por nome do jogador
        jogadores = {}
        for row in resultados:
            nome = row.nome
            if nome not in jogadores:
                jogadores[nome] = {
                    'nome': nome,
                    'total_pontos': 0,
                    'total_sets': 0,
                    'total_jogos': 0,
                    'campeonatos': []
                }
            jogadores[nome]['total_pontos'] += row.total_pontos or 0
            jogadores[nome]['total_sets'] += row.total_sets or 0
            jogadores[nome]['total_jogos'] += row.total_jogos or 0
            jogadores[nome]['campeonatos'].append({
                'id': row.campeonato_id,
                'nome': row.campeonato_nome,
                'pontos': row.total_pontos or 0,
                'sets': row.total_sets or 0,
                'jogos': row.total_jogos or 0
            })

        # Também incluir jogadores sem vínculo com jogador_inscrito (jogadores avulsos)
        avulsos = (
            db.session.query(
                Jogador.nome,
                Campeonato.nome.label('campeonato_nome'),
                Campeonato.id.label('campeonato_id'),
                func.sum(Jogador.pontos_marcados).label('total_pontos'),
                func.sum(Jogador.sets_vencidos).label('total_sets'),
                func.count(Jogador.id).label('total_jogos')
            )
            .join(Mesa, Mesa.id == Jogador.mesa_id)
            .join(Campeonato, Campeonato.id == Mesa.campeonato_id)
            .filter(Jogador.jogador_inscrito_id == None)
            .group_by(Jogador.nome, Campeonato.id, Campeonato.nome)
            .all()
        )

        for row in avulsos:
            nome = row.nome
            if nome not in jogadores:
                jogadores[nome] = {
                    'nome': nome,
                    'total_pontos': 0,
                    'total_sets': 0,
                    'total_jogos': 0,
                    'campeonatos': []
                }
            jogadores[nome]['total_pontos'] += row.total_pontos or 0
            jogadores[nome]['total_sets'] += row.total_sets or 0
            jogadores[nome]['total_jogos'] += row.total_jogos or 0
            jogadores[nome]['campeonatos'].append({
                'id': row.campeonato_id,
                'nome': row.campeonato_nome,
                'pontos': row.total_pontos or 0,
                'sets': row.total_sets or 0,
                'jogos': row.total_jogos or 0
            })

        # Ordenar por total de pontos (decrescente), desempate por sets vencidos
        return sorted(jogadores.values(), key=lambda x: (x['total_pontos'], x['total_sets']), reverse=True)

    try:
        return jsonify(consultar_ranking())
    except OperationalError:
        # Em cenários de banco vazio/recém recriado, tenta recuperar as tabelas e repetir.
        db.session.rollback()
        db.create_all()
        try:
            return jsonify(consultar_ranking())
        except Exception:
            db.session.rollback()
            return jsonify([])
