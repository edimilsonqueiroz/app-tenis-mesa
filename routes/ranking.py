from flask import Blueprint, jsonify
from chaveamento import registrar_resultado_por_mesa
from models import db, Jogador, JogadorInscrito, Mesa, Campeonato, ResultadoPartida
from sqlalchemy import func
from sqlalchemy.exc import OperationalError

bp = Blueprint('ranking', __name__, url_prefix='/api/ranking')


@bp.route('', methods=['GET'])
def obter_ranking():
    """
    Retorna o ranking geral de TODOS os jogadores cadastrados.
    Mostra dados zerados para jogadores que não participaram de campeonatos.
    """
    def consultar_ranking():
        # Dicionário para agregar dados por jogador
        jogadores = {}
        
        # 1. Primeiro, adicionar TODOS os JogadorInscrito cadastrados (com dados zerados)
        jogadores_inscritos = JogadorInscrito.query.all()
        for ji in jogadores_inscritos:
            if ji.nome not in jogadores:
                jogadores[ji.nome] = {
                    'nome': ji.nome,
                    'total_pontos': 0,
                    'total_sets': 0,
                    'total_jogos': 0,
                    'campeonatos': {}
                }
        
        # 2. Adicionar todos os Jogador (avulsos) que não estão em JogadorInscrito
        jogadores_avulsos = Jogador.query.filter_by(jogador_inscrito_id=None).all()
        for jog in jogadores_avulsos:
            if jog.nome not in jogadores:
                jogadores[jog.nome] = {
                    'nome': jog.nome,
                    'total_pontos': 0,
                    'total_sets': 0,
                    'total_jogos': 0,
                    'campeonatos': {}
                }
        
        # 3. Processar resultados de partidas concluídas (histórico) para atualizar dados
        resultados = ResultadoPartida.query.all()
        
        for resultado in resultados:
            # Processar Time 1
            if resultado.jogadores_time1 and resultado.jogadores_time1 != 'Vazio':
                nomes_time1 = resultado.jogadores_time1.split(' & ')
                for nome in nomes_time1:
                    nome = nome.strip()
                    if nome:
                        if nome not in jogadores:
                            jogadores[nome] = {
                                'nome': nome,
                                'total_pontos': 0,
                                'total_sets': 0,
                                'total_jogos': 0,
                                'campeonatos': {}
                            }
                        
                        # Adicionar pontos e sets do resultado
                        if resultado.vencedor_time == 1:
                            jogadores[nome]['total_sets'] += resultado.sets_time1
                        else:
                            jogadores[nome]['total_sets'] += resultado.sets_time1
                        
                        jogadores[nome]['total_pontos'] += resultado.pontos_time1
                        jogadores[nome]['total_jogos'] += 1
                        
                        # Rastrear campeonatos
                        if resultado.campeonato_id not in jogadores[nome]['campeonatos']:
                            jogadores[nome]['campeonatos'][resultado.campeonato_id] = {
                                'id': resultado.campeonato_id,
                                'nome': '',
                                'pontos': 0,
                                'sets': 0,
                                'jogos': 0
                            }
                        
                        jogadores[nome]['campeonatos'][resultado.campeonato_id]['pontos'] += resultado.pontos_time1
                        jogadores[nome]['campeonatos'][resultado.campeonato_id]['sets'] += resultado.sets_time1
                        jogadores[nome]['campeonatos'][resultado.campeonato_id]['jogos'] += 1
            
            # Processar Time 2
            if resultado.jogadores_time2 and resultado.jogadores_time2 != 'Vazio':
                nomes_time2 = resultado.jogadores_time2.split(' & ')
                for nome in nomes_time2:
                    nome = nome.strip()
                    if nome:
                        if nome not in jogadores:
                            jogadores[nome] = {
                                'nome': nome,
                                'total_pontos': 0,
                                'total_sets': 0,
                                'total_jogos': 0,
                                'campeonatos': {}
                            }
                        
                        # Adicionar pontos e sets do resultado
                        if resultado.vencedor_time == 2:
                            jogadores[nome]['total_sets'] += resultado.sets_time2
                        else:
                            jogadores[nome]['total_sets'] += resultado.sets_time2
                        
                        jogadores[nome]['total_pontos'] += resultado.pontos_time2
                        jogadores[nome]['total_jogos'] += 1
                        
                        # Rastrear campeonatos
                        if resultado.campeonato_id not in jogadores[nome]['campeonatos']:
                            jogadores[nome]['campeonatos'][resultado.campeonato_id] = {
                                'id': resultado.campeonato_id,
                                'nome': '',
                                'pontos': 0,
                                'sets': 0,
                                'jogos': 0
                            }
                        
                        jogadores[nome]['campeonatos'][resultado.campeonato_id]['pontos'] += resultado.pontos_time2
                        jogadores[nome]['campeonatos'][resultado.campeonato_id]['sets'] += resultado.sets_time2
                        jogadores[nome]['campeonatos'][resultado.campeonato_id]['jogos'] += 1
        
        # 4. Preencher nomes de campeonatos
        for nome_jogador in jogadores:
            campeonatos_list = []
            for campeonato_id, dados in jogadores[nome_jogador]['campeonatos'].items():
                campeonato = Campeonato.query.get(campeonato_id)
                if campeonato:
                    dados['nome'] = campeonato.nome
                campeonatos_list.append(dados)
            
            jogadores[nome_jogador]['campeonatos'] = campeonatos_list
        
        # 5. Ordenar por total de pontos e sets vencidos (desempate)
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
