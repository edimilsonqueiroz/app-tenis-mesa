import math
from collections import defaultdict

from models import ChaveamentoPartida, ClassificacaoGrupo, GrupoChaveamento, Jogador, JogadorInscrito, Mesa, PartidaGrupo, db


def normalizar_categoria(valor):
    categoria = (valor or 'Geral').strip()
    return categoria or 'Geral'


def nome_rodada_por_partidas(total_partidas):
    nomes = {
        1: 'Final',
        2: 'Semifinais',
        4: 'Quartas de final',
        8: 'Oitavas de final'
    }
    return nomes.get(total_partidas, f'Rodada com {total_partidas} partidas')


def nome_rodada_por_numero(rodada, total_rodadas):
    partidas = 2 ** max(total_rodadas - rodada, 0)
    return nome_rodada_por_partidas(partidas)


def resumo_inscrito(inscrito):
    if not inscrito:
        return None

    return {
        'id': inscrito.id,
        'nome': inscrito.nome,
        'categoria': inscrito.categoria,
        'campeonato_id': inscrito.campeonato_id
    }


def _proxima_potencia_de_dois(valor):
    tamanho = 1
    while tamanho < valor:
        tamanho *= 2
    return tamanho


def _query_jogadores_ativos(campeonato_id):
    return (
        JogadorInscrito.query
        .filter_by(campeonato_id=campeonato_id, ativo=True)
        .order_by(JogadorInscrito.categoria.asc(), JogadorInscrito.data_inscricao.asc(), JogadorInscrito.id.asc())
    )


def montar_preview_categoria(jogadores):
    jogadores_ordenados = sorted(
        jogadores,
        key=lambda jogador: (jogador.data_inscricao or jogador.id, jogador.id)
    )
    total_jogadores = len(jogadores_ordenados)

    if total_jogadores == 0:
        return {
            'modo': 'simulacao',
            'total_jogadores': 0,
            'tamanho_chave': 0,
            'rodadas': [],
            'campeao': None,
            'campeao_provisorio': None
        }

    if total_jogadores == 1:
        return {
            'modo': 'simulacao',
            'total_jogadores': 1,
            'tamanho_chave': 1,
            'rodadas': [],
            'campeao': resumo_inscrito(jogadores_ordenados[0]),
            'campeao_provisorio': resumo_inscrito(jogadores_ordenados[0])
        }

    tamanho_chave = _proxima_potencia_de_dois(total_jogadores)
    participantes = [resumo_inscrito(jogador) for jogador in jogadores_ordenados]
    participantes.extend([None] * (tamanho_chave - total_jogadores))

    rodadas = []
    slots_rodada = participantes
    numero_rodada = 1

    while len(slots_rodada) >= 2:
        partidas = []
        proximos_slots = []

        for indice in range(0, len(slots_rodada), 2):
            jogador_1 = slots_rodada[indice]
            jogador_2 = slots_rodada[indice + 1]
            avanca_automaticamente = (jogador_1 is None) ^ (jogador_2 is None)

            if avanca_automaticamente:
                proximos_slots.append(jogador_1 or jogador_2)
            else:
                proximos_slots.append(None)

            partidas.append({
                'id': None,
                'numero': len(partidas) + 1,
                'jogador_1': jogador_1,
                'jogador_2': jogador_2,
                'vencedor': jogador_1 or jogador_2 if avanca_automaticamente else None,
                'avanca_automaticamente': avanca_automaticamente,
                'status': 'bye' if avanca_automaticamente else 'pendente',
                'mesa': None,
                'placar': None
            })

        rodadas.append({
            'numero': numero_rodada,
            'nome': nome_rodada_por_partidas(len(partidas)),
            'partidas': partidas
        })

        if len(proximos_slots) == 1:
            break

        slots_rodada = proximos_slots
        numero_rodada += 1

    return {
        'modo': 'simulacao',
        'total_jogadores': total_jogadores,
        'tamanho_chave': tamanho_chave,
        'rodadas': rodadas,
        'campeao': None,
        'campeao_provisorio': None
    }


def _deletar_partidas_existentes(campeonato_id):
    partidas = ChaveamentoPartida.query.filter_by(campeonato_id=campeonato_id).all()
    for partida in partidas:
        db.session.delete(partida)
    db.session.flush()


def _criar_arvore_partidas(campeonato_id, categoria, participantes, partidas_por_rodada):
    tamanho_segmento = len(participantes)

    if tamanho_segmento == 1:
        participante = participantes[0]
        return {
            'contagem': 1 if participante else 0,
            'vencedor': participante,
            'partida': None
        }

    metade = tamanho_segmento // 2
    esquerda = _criar_arvore_partidas(campeonato_id, categoria, participantes[:metade], partidas_por_rodada)
    direita = _criar_arvore_partidas(campeonato_id, categoria, participantes[metade:], partidas_por_rodada)

    rodada = int(math.log2(tamanho_segmento))
    posicao = len(partidas_por_rodada[rodada]) + 1

    partida = ChaveamentoPartida(
        campeonato_id=campeonato_id,
        categoria=categoria,
        rodada=rodada,
        posicao=posicao,
        jogador_1=esquerda['vencedor'],
        jogador_2=direita['vencedor']
    )
    db.session.add(partida)
    partidas_por_rodada[rodada].append(partida)

    if esquerda['partida']:
        esquerda['partida'].proxima_partida = partida
        esquerda['partida'].proximo_slot = 1
    if direita['partida']:
        direita['partida'].proxima_partida = partida
        direita['partida'].proximo_slot = 2

    contagem = esquerda['contagem'] + direita['contagem']
    vencedor = None

    if contagem == 0:
        partida.status = 'vazio'
    elif contagem == 1:
        partida.status = 'bye'
        vencedor = esquerda['vencedor'] or direita['vencedor']
        partida.vencedor = vencedor
    elif partida.jogador_1 and partida.jogador_2:
        partida.status = 'pronta'
    else:
        partida.status = 'pendente'

    return {
        'contagem': contagem,
        'vencedor': vencedor,
        'partida': partida
    }


def _buscar_filhos(partida):
    filhos = ChaveamentoPartida.query.filter_by(proxima_partida_id=partida.id).all()
    por_slot = {filho.proximo_slot: filho for filho in filhos}
    return por_slot.get(1), por_slot.get(2)


def _resetar_placar_mesa(mesa):
    if not mesa.placar:
        return

    placar = mesa.placar
    placar.pontos_time1 = 0
    placar.pontos_time2 = 0
    placar.set_numero = 1
    placar.sets_time1 = 0
    placar.sets_time2 = 0
    placar.servidor_inicial_jogo = 1
    placar.servidor_time = 1
    placar.serves_no_set = 0
    placar.lados_invertidos = False
    placar.status = 'em_andamento'


def sincronizar_mesa_com_partida(partida, mesa=None):
    mesa = mesa or partida.mesa
    if not mesa:
        return partida

    Jogador.query.filter_by(mesa_id=mesa.id).delete(synchronize_session=False)
    _resetar_placar_mesa(mesa)

    participantes = [
        (1, partida.jogador_1),
        (2, partida.jogador_2)
    ]

    for time, inscrito in participantes:
        if not inscrito:
            continue

        db.session.add(Jogador(
            nome=inscrito.nome,
            mesa_id=mesa.id,
            time=time,
            jogador_inscrito_id=inscrito.id
        ))

    total_participantes = sum(1 for _, inscrito in participantes if inscrito)
    mesa.status = 'em_uso' if total_participantes == 2 else 'disponivel'

    if partida.status not in ('finalizada', 'bye', 'vazio'):
        if total_participantes == 2 and partida.mesa_id:
            partida.status = 'em_andamento'
        elif total_participantes == 2:
            partida.status = 'pronta'
        elif total_participantes == 1:
            partida.status = 'pendente'
        else:
            partida.status = 'vazio'

    return partida


def _atualizar_status_partida(partida):
    if not partida:
        return

    if partida.vencedor_inscrito_id:
        partida.status = 'finalizada' if partida.placar_sets_time1 is not None or partida.placar_sets_time2 is not None else 'bye'
        if partida.mesa:
            sincronizar_mesa_com_partida(partida, partida.mesa)
        return

    filho_1, filho_2 = _buscar_filhos(partida)
    slot_1_bloqueado = filho_1 is not None and filho_1.status == 'vazio'
    slot_2_bloqueado = filho_2 is not None and filho_2.status == 'vazio'

    if partida.jogador_1 and partida.jogador_2:
        partida.status = 'em_andamento' if partida.mesa_id else 'pronta'
    elif partida.jogador_1 and slot_2_bloqueado:
        partida.vencedor = partida.jogador_1
        partida.status = 'bye'
        _propagar_vencedor(partida)
        return
    elif partida.jogador_2 and slot_1_bloqueado:
        partida.vencedor = partida.jogador_2
        partida.status = 'bye'
        _propagar_vencedor(partida)
        return
    elif slot_1_bloqueado and slot_2_bloqueado and not partida.jogador_1 and not partida.jogador_2:
        partida.status = 'vazio'
    else:
        partida.status = 'pendente'

    if partida.mesa:
        sincronizar_mesa_com_partida(partida, partida.mesa)


def _propagar_vencedor(partida):
    proxima = partida.proxima_partida
    if not proxima or not partida.vencedor:
        return

    if partida.proximo_slot == 1:
        proxima.jogador_1 = partida.vencedor
    elif partida.proximo_slot == 2:
        proxima.jogador_2 = partida.vencedor

    _atualizar_status_partida(proxima)


def gerar_chaveamento_vivo(campeonato_id):
    _deletar_partidas_existentes(campeonato_id)

    jogadores_por_categoria = defaultdict(list)
    for jogador in _query_jogadores_ativos(campeonato_id).all():
        jogadores_por_categoria[normalizar_categoria(jogador.categoria)].append(jogador)

    for categoria, jogadores in jogadores_por_categoria.items():
        if len(jogadores) < 2:
            continue

        tamanho_chave = _proxima_potencia_de_dois(len(jogadores))
        participantes = list(jogadores) + [None] * (tamanho_chave - len(jogadores))
        partidas_por_rodada = defaultdict(list)
        _criar_arvore_partidas(campeonato_id, categoria, participantes, partidas_por_rodada)

    db.session.flush()
    return obter_chaveamento_serializado(campeonato_id)


def alocar_partida_em_mesa(campeonato_id, partida_id, mesa_id):
    partida = ChaveamentoPartida.query.get(partida_id)
    mesa = Mesa.query.get(mesa_id)

    if not partida or partida.campeonato_id != campeonato_id:
        raise ValueError('Partida de chaveamento não encontrada')

    if not mesa or mesa.campeonato_id != campeonato_id:
        raise ValueError('Mesa não encontrada para este campeonato')

    outra_partida = (
        ChaveamentoPartida.query
        .filter(ChaveamentoPartida.mesa_id == mesa.id, ChaveamentoPartida.id != partida.id)
        .filter(ChaveamentoPartida.status.in_(['pendente', 'pronta', 'em_andamento']))
        .first()
    )
    if outra_partida:
        raise ValueError('Esta mesa já está vinculada a outra partida ativa do chaveamento')

    partida.mesa = mesa
    sincronizar_mesa_com_partida(partida, mesa)
    db.session.flush()
    return partida


def liberar_mesa_para_proxima_partida(campeonato_id, partida_id):
    partida = ChaveamentoPartida.query.get(partida_id)
    if not partida or partida.campeonato_id != campeonato_id:
        raise ValueError('Partida de chaveamento não encontrada')

    if partida.status != 'finalizada':
        raise ValueError('Só é possível liberar a mesa de uma partida já finalizada')

    if not partida.mesa:
        raise ValueError('Esta partida não está vinculada a nenhuma mesa')

    mesa = partida.mesa
    partida.mesa_id = None

    proxima = partida.proxima_partida
    if proxima and proxima.status == 'pronta':
        proxima.mesa = mesa
        sincronizar_mesa_com_partida(proxima, mesa)
        db.session.flush()
        return proxima

    # Nenhuma próxima partida pronta — apenas reseta a mesa
    Jogador.query.filter_by(mesa_id=mesa.id).delete(synchronize_session=False)
    _resetar_placar_mesa(mesa)
    mesa.status = 'disponivel'
    db.session.flush()
    return None


def registrar_resultado_partida_por_mesa(mesa, vencedor_time):
    if not mesa:
        return None

    partida = (
        ChaveamentoPartida.query
        .filter_by(mesa_id=mesa.id)
        .filter(ChaveamentoPartida.status.in_(['pendente', 'pronta', 'em_andamento']))
        .order_by(ChaveamentoPartida.rodada.desc(), ChaveamentoPartida.posicao.desc())
        .first()
    )
    if not partida:
        return None

    jogador_vencedor = next(
        (jogador for jogador in mesa.jogadores if jogador.time == vencedor_time and jogador.jogador_inscrito_id),
        None
    )
    if not jogador_vencedor:
        return None

    partida.vencedor_inscrito_id = jogador_vencedor.jogador_inscrito_id
    partida.placar_sets_time1 = mesa.placar.sets_time1 if mesa.placar else None
    partida.placar_sets_time2 = mesa.placar.sets_time2 if mesa.placar else None
    partida.status = 'finalizada'

    _propagar_vencedor(partida)
    return partida


def _serializar_partida(partida):
    placar = None
    if partida.placar_sets_time1 is not None or partida.placar_sets_time2 is not None:
        placar = {
            'sets_time1': partida.placar_sets_time1,
            'sets_time2': partida.placar_sets_time2
        }
    elif partida.mesa and partida.mesa.placar:
        placar = {
            'sets_time1': partida.mesa.placar.sets_time1,
            'sets_time2': partida.mesa.placar.sets_time2,
            'pontos_time1': partida.mesa.placar.pontos_time1,
            'pontos_time2': partida.mesa.placar.pontos_time2,
            'status': partida.mesa.placar.status
        }

    return {
        'id': partida.id,
        'numero': partida.posicao,
        'status': partida.status,
        'jogador_1': resumo_inscrito(partida.jogador_1),
        'jogador_2': resumo_inscrito(partida.jogador_2),
        'vencedor': resumo_inscrito(partida.vencedor),
        'avanca_automaticamente': partida.status == 'bye',
        'mesa': {
            'id': partida.mesa.id,
            'numero': partida.mesa.numero,
            'status': partida.mesa.status
        } if partida.mesa else None,
        'placar': placar
    }


def obter_chaveamento_serializado(campeonato_id, campeonato=None):
    partidas = (
        ChaveamentoPartida.query
        .filter_by(campeonato_id=campeonato_id)
        .order_by(ChaveamentoPartida.categoria.asc(), ChaveamentoPartida.rodada.asc(), ChaveamentoPartida.posicao.asc())
        .all()
    )

    jogadores = _query_jogadores_ativos(campeonato_id).all()
    jogadores_por_categoria = defaultdict(list)
    for jogador in jogadores:
        jogadores_por_categoria[normalizar_categoria(jogador.categoria)].append(jogador)

    if not partidas:
        categorias_preview = []
        for categoria, jogadores_categoria in jogadores_por_categoria.items():
            categorias_preview.append({
                'categoria': categoria,
                **montar_preview_categoria(jogadores_categoria)
            })

        return {
            'campeonato_id': campeonato_id,
            'formato': 'eliminacao_simples',
            'modo': 'simulacao',
            'categorias': categorias_preview
        }

    partidas_por_categoria = defaultdict(list)
    for partida in partidas:
        partidas_por_categoria[partida.categoria].append(partida)

    categorias_serializadas = []
    for categoria, partidas_categoria in partidas_por_categoria.items():
        rodadas_dict = defaultdict(list)
        total_rodadas = max(partida.rodada for partida in partidas_categoria)

        for partida in partidas_categoria:
            rodadas_dict[partida.rodada].append(partida)

        rodadas = []
        for rodada_numero in sorted(rodadas_dict.keys()):
            rodadas.append({
                'numero': rodada_numero,
                'nome': nome_rodada_por_numero(rodada_numero, total_rodadas),
                'partidas': [_serializar_partida(partida) for partida in sorted(rodadas_dict[rodada_numero], key=lambda item: item.posicao)]
            })

        total_jogadores = len(jogadores_por_categoria.get(categoria, []))
        final = next((partida for partida in partidas_categoria if partida.rodada == total_rodadas), None)
        campeao = resumo_inscrito(final.vencedor) if final and final.vencedor else None
        campeao_provisorio = None

        if total_jogadores == 1:
            campeao = resumo_inscrito(jogadores_por_categoria[categoria][0])
            campeao_provisorio = campeao

        categorias_serializadas.append({
            'categoria': categoria,
            'modo': 'vivo',
            'total_jogadores': total_jogadores,
            'tamanho_chave': 2 ** total_rodadas,
            'rodadas': rodadas,
            'campeao': campeao,
            'campeao_provisorio': campeao_provisorio
        })

    for categoria, jogadores_categoria in jogadores_por_categoria.items():
        if categoria in partidas_por_categoria:
            continue

        categorias_serializadas.append({
            'categoria': categoria,
            **montar_preview_categoria(jogadores_categoria)
        })

    categorias_serializadas.sort(key=lambda item: item['categoria'])

    return {
        'campeonato_id': campeonato_id,
        'formato': 'eliminacao_simples',
        'modo': 'vivo',
        'categorias': categorias_serializadas
    }


# ============================================================
# FASE DE GRUPOS
# ============================================================

def _gerar_schedule_round_robin(participantes):
    """Gera rodadas round-robin (método berger) para uma lista de participantes."""
    lista = list(participantes)
    n = len(lista)
    if n <= 1:
        return []
    if n % 2 == 1:
        lista.append(None)
        n += 1

    rodadas = []
    for _ in range(n - 1):
        rodada = []
        for i in range(n // 2):
            j1 = lista[i]
            j2 = lista[n - 1 - i]
            if j1 is not None and j2 is not None:
                rodada.append((j1, j2))
        if rodada:
            rodadas.append(rodada)
        # Rotaciona mantendo o primeiro fixo
        lista = [lista[0]] + [lista[-1]] + lista[1:-1]
    return rodadas


def _deletar_grupos_existentes(campeonato_id):
    grupos = GrupoChaveamento.query.filter_by(campeonato_id=campeonato_id).all()
    for g in grupos:
        db.session.delete(g)
    db.session.flush()


def gerar_fase_grupos(campeonato_id, jogadores_por_grupo=4):
    """Gera a fase de grupos round-robin para cada categoria do campeonato."""
    _deletar_grupos_existentes(campeonato_id)
    _deletar_partidas_existentes(campeonato_id)

    jogadores_por_categoria = defaultdict(list)
    for jogador in _query_jogadores_ativos(campeonato_id).all():
        jogadores_por_categoria[normalizar_categoria(jogador.categoria)].append(jogador)

    for categoria, jogadores in jogadores_por_categoria.items():
        if len(jogadores) < 2:
            continue

        n = len(jogadores)
        num_grupos_tentativo = max(1, n // jogadores_por_grupo)

        grupos_membros = [[] for _ in range(num_grupos_tentativo)]
        for i, jogador in enumerate(jogadores):
            grupos_membros[i % num_grupos_tentativo].append(jogador)

        # Mescla grupos com apenas 1 membro no grupo anterior
        grupos_finais = []
        pendente = []
        for membros in grupos_membros:
            todos = pendente + membros
            if len(todos) >= 2:
                grupos_finais.append(todos)
                pendente = []
            else:
                pendente = todos
        if pendente and grupos_finais:
            grupos_finais[-1].extend(pendente)

        for numero, membros in enumerate(grupos_finais, start=1):
            grupo = GrupoChaveamento(
                campeonato_id=campeonato_id,
                categoria=categoria,
                numero=numero,
                status='pendente'
            )
            db.session.add(grupo)
            db.session.flush()

            for membro in membros:
                db.session.add(ClassificacaoGrupo(
                    grupo_id=grupo.id,
                    jogador_inscrito_id=membro.id
                ))

            schedule = _gerar_schedule_round_robin(membros)
            posicao = 1
            for rodada_num, rodada in enumerate(schedule, start=1):
                for j1, j2 in rodada:
                    db.session.add(PartidaGrupo(
                        campeonato_id=campeonato_id,
                        grupo_id=grupo.id,
                        categoria=categoria,
                        rodada_grupo=rodada_num,
                        posicao=posicao,
                        status='pronta',
                        jogador_1_inscrito_id=j1.id,
                        jogador_2_inscrito_id=j2.id
                    ))
                    posicao += 1
            db.session.flush()

    return obter_estado_torneio(campeonato_id)


def calcular_posicoes_grupo(grupo):
    """Calcula e persiste as posições finais em um grupo."""
    classifs = ClassificacaoGrupo.query.filter_by(grupo_id=grupo.id).all()

    def chave(c):
        diff = c.sets_vencidos - c.sets_perdidos
        return (-c.pontos, -diff, -c.sets_vencidos)

    classifs_sorted = sorted(classifs, key=chave)
    for pos, c in enumerate(classifs_sorted, start=1):
        c.posicao_final = pos
    return classifs_sorted


def atualizar_classificacao_grupo(partida_grupo):
    """Atualiza a classificação do grupo após um resultado registrado."""
    grupo = partida_grupo.grupo
    v_id = partida_grupo.vencedor_inscrito_id
    if not v_id:
        return

    j1_id = partida_grupo.jogador_1_inscrito_id
    j2_id = partida_grupo.jogador_2_inscrito_id
    perdedor_id = j2_id if v_id == j1_id else j1_id

    sets1 = partida_grupo.placar_sets_time1 or 0
    sets2 = partida_grupo.placar_sets_time2 or 0
    sets_v, sets_p = (sets1, sets2) if v_id == j1_id else (sets2, sets1)

    c_v = ClassificacaoGrupo.query.filter_by(grupo_id=grupo.id, jogador_inscrito_id=v_id).first()
    c_p = ClassificacaoGrupo.query.filter_by(grupo_id=grupo.id, jogador_inscrito_id=perdedor_id).first()

    if c_v:
        c_v.pontos += 2
        c_v.partidas_vencidas += 1
        c_v.sets_vencidos += sets_v
        c_v.sets_perdidos += sets_p
    if c_p:
        c_p.partidas_perdidas += 1
        c_p.sets_vencidos += sets_p
        c_p.sets_perdidos += sets_v

    partidas = PartidaGrupo.query.filter_by(grupo_id=grupo.id).all()
    if all(p.status == 'finalizada' for p in partidas):
        grupo.status = 'finalizado'
        calcular_posicoes_grupo(grupo)


def verificar_todos_grupos_finalizados(campeonato_id):
    grupos = GrupoChaveamento.query.filter_by(campeonato_id=campeonato_id).all()
    if not grupos:
        return False
    return all(g.status == 'finalizado' for g in grupos)


def avancar_para_mata_mata(campeonato_id, qtd_avancam=2):
    """Gera o chaveamento eliminatório com os classificados da fase de grupos."""
    if not verificar_todos_grupos_finalizados(campeonato_id):
        raise ValueError('Ainda há partidas de grupo pendentes. Finalize todos os jogos antes de avançar.')

    _deletar_partidas_existentes(campeonato_id)

    grupos_por_categoria = defaultdict(list)
    for g in GrupoChaveamento.query.filter_by(campeonato_id=campeonato_id).order_by(
        GrupoChaveamento.categoria.asc(), GrupoChaveamento.numero.asc()
    ).all():
        grupos_por_categoria[g.categoria].append(g)

    for categoria, grupos_cat in grupos_por_categoria.items():
        classificados_por_pos = defaultdict(list)
        for grupo in grupos_cat:
            classifs = ClassificacaoGrupo.query.filter_by(grupo_id=grupo.id).order_by(
                ClassificacaoGrupo.posicao_final.asc()
            ).all()
            for c in classifs:
                if c.posicao_final and c.posicao_final <= qtd_avancam:
                    classificados_por_pos[c.posicao_final].append(c.jogador)
                    c.avancou = True

        # Snake seeding: 1os em ordem, 2os em ordem reversa, etc.
        participantes = []
        for pos in range(1, qtd_avancam + 1):
            lista = classificados_por_pos.get(pos, [])
            participantes.extend(lista if pos % 2 == 1 else reversed(lista))

        if len(participantes) < 2:
            continue

        tamanho_chave = _proxima_potencia_de_dois(len(participantes))
        participantes_com_byes = participantes + [None] * (tamanho_chave - len(participantes))
        partidas_por_rodada = defaultdict(list)
        _criar_arvore_partidas(campeonato_id, categoria, participantes_com_byes, partidas_por_rodada)
        db.session.flush()

    return obter_estado_torneio(campeonato_id)


def alocar_partida_grupo_em_mesa(campeonato_id, partida_id, mesa_id):
    partida = PartidaGrupo.query.get(partida_id)
    mesa = Mesa.query.get(mesa_id)

    if not partida or partida.campeonato_id != campeonato_id:
        raise ValueError('Partida de grupo não encontrada')
    if not mesa or mesa.campeonato_id != campeonato_id:
        raise ValueError('Mesa não encontrada para este campeonato')
    if partida.status == 'finalizada':
        raise ValueError('Esta partida já foi finalizada')

    outra = (
        PartidaGrupo.query
        .filter(PartidaGrupo.mesa_id == mesa.id, PartidaGrupo.id != partida.id)
        .filter(PartidaGrupo.status.in_(['pronta', 'em_andamento']))
        .first()
    ) or (
        ChaveamentoPartida.query
        .filter(ChaveamentoPartida.mesa_id == mesa.id)
        .filter(ChaveamentoPartida.status.in_(['pendente', 'pronta', 'em_andamento']))
        .first()
    )
    if outra:
        raise ValueError('Esta mesa já está vinculada a outra partida ativa')

    partida.mesa_id = mesa.id
    partida.status = 'em_andamento'

    Jogador.query.filter_by(mesa_id=mesa.id).delete(synchronize_session=False)
    _resetar_placar_mesa(mesa)

    for time, inscrito in [(1, partida.jogador_1), (2, partida.jogador_2)]:
        if not inscrito:
            continue
        db.session.add(Jogador(
            nome=inscrito.nome,
            mesa_id=mesa.id,
            time=time,
            jogador_inscrito_id=inscrito.id
        ))

    mesa.status = 'em_uso'
    db.session.flush()
    return partida


def liberar_mesa_partida_grupo(campeonato_id, partida_id):
    partida = PartidaGrupo.query.get(partida_id)
    if not partida or partida.campeonato_id != campeonato_id:
        raise ValueError('Partida de grupo não encontrada')
    if partida.status != 'finalizada':
        raise ValueError('Só é possível liberar a mesa de uma partida já finalizada')
    if not partida.mesa_id:
        raise ValueError('Esta partida não está vinculada a nenhuma mesa')

    mesa = partida.mesa
    partida.mesa_id = None
    Jogador.query.filter_by(mesa_id=mesa.id).delete(synchronize_session=False)
    _resetar_placar_mesa(mesa)
    mesa.status = 'disponivel'
    db.session.flush()


def registrar_resultado_partida_grupo_por_mesa(mesa, vencedor_time):
    """Registra resultado de uma partida de grupo quando um jogo termina na mesa."""
    if not mesa:
        return None

    partida = (
        PartidaGrupo.query
        .filter_by(mesa_id=mesa.id)
        .filter(PartidaGrupo.status.in_(['pronta', 'em_andamento']))
        .first()
    )
    if not partida:
        return None

    jogador_vencedor = next(
        (j for j in mesa.jogadores if j.time == vencedor_time and j.jogador_inscrito_id),
        None
    )
    if not jogador_vencedor:
        return None

    partida.vencedor_inscrito_id = jogador_vencedor.jogador_inscrito_id
    partida.placar_sets_time1 = mesa.placar.sets_time1 if mesa.placar else None
    partida.placar_sets_time2 = mesa.placar.sets_time2 if mesa.placar else None
    partida.status = 'finalizada'
    atualizar_classificacao_grupo(partida)
    return partida


def registrar_resultado_por_mesa(mesa, vencedor_time):
    """Dispatcher: tenta registrar resultado em partida de grupo ou mata-mata."""
    resultado_grupo = registrar_resultado_partida_grupo_por_mesa(mesa, vencedor_time)
    if resultado_grupo:
        return 'grupo', resultado_grupo

    resultado_ko = registrar_resultado_partida_por_mesa(mesa, vencedor_time)
    if resultado_ko:
        return 'mata_mata', resultado_ko

    return None, None


# ============================================================
# SERIALIZAÇÃO DO ESTADO COMPLETO DO TORNEIO
# ============================================================

def _serializar_classificacao(c):
    return {
        'jogador': resumo_inscrito(c.jogador),
        'pontos': c.pontos,
        'partidas_vencidas': c.partidas_vencidas,
        'partidas_perdidas': c.partidas_perdidas,
        'sets_vencidos': c.sets_vencidos,
        'sets_perdidos': c.sets_perdidos,
        'posicao': c.posicao_final,
        'avancou': c.avancou
    }


def _serializar_partida_grupo(p):
    placar = None
    if p.placar_sets_time1 is not None:
        placar = {'sets_time1': p.placar_sets_time1, 'sets_time2': p.placar_sets_time2}
    elif p.mesa and p.mesa.placar:
        pl = p.mesa.placar
        placar = {
            'sets_time1': pl.sets_time1,
            'sets_time2': pl.sets_time2,
            'pontos_time1': pl.pontos_time1,
            'pontos_time2': pl.pontos_time2,
            'status': pl.status
        }
    return {
        'id': p.id,
        'rodada_grupo': p.rodada_grupo,
        'posicao': p.posicao,
        'status': p.status,
        'jogador_1': resumo_inscrito(p.jogador_1),
        'jogador_2': resumo_inscrito(p.jogador_2),
        'vencedor': resumo_inscrito(p.vencedor),
        'mesa': {'id': p.mesa.id, 'numero': p.mesa.numero, 'status': p.mesa.status} if p.mesa else None,
        'placar': placar
    }


def _serializar_grupo(grupo):
    classifs = ClassificacaoGrupo.query.filter_by(grupo_id=grupo.id).all()

    def sort_key(c):
        if c.posicao_final is not None:
            return c.posicao_final
        diff = c.sets_vencidos - c.sets_perdidos
        return 1000 - c.pontos * 100 - diff

    classifs_sorted = sorted(classifs, key=sort_key)
    partidas = PartidaGrupo.query.filter_by(grupo_id=grupo.id).order_by(
        PartidaGrupo.rodada_grupo.asc(), PartidaGrupo.posicao.asc()
    ).all()

    return {
        'id': grupo.id,
        'numero': grupo.numero,
        'status': grupo.status,
        'classificacao': [_serializar_classificacao(c) for c in classifs_sorted],
        'partidas': [_serializar_partida_grupo(p) for p in partidas]
    }


def obter_estado_torneio(campeonato_id):
    """Retorna o estado completo do torneio: fase de grupos + mata-mata."""
    grupos = GrupoChaveamento.query.filter_by(campeonato_id=campeonato_id).order_by(
        GrupoChaveamento.categoria.asc(), GrupoChaveamento.numero.asc()
    ).all()

    tem_grupos = len(grupos) > 0
    todos_grupos_finalizados = tem_grupos and all(g.status == 'finalizado' for g in grupos)

    partidas_ko = ChaveamentoPartida.query.filter_by(campeonato_id=campeonato_id).first()
    tem_mata_mata = partidas_ko is not None

    if tem_grupos:
        if todos_grupos_finalizados and tem_mata_mata:
            fase_atual = 'mata_mata'
        elif todos_grupos_finalizados:
            fase_atual = 'aguardando_avanco'
        else:
            fase_atual = 'grupos'
    elif tem_mata_mata:
        fase_atual = 'mata_mata'
    else:
        fase_atual = 'sem_dados'

    jogadores = _query_jogadores_ativos(campeonato_id).all()
    categorias_set = sorted(set(normalizar_categoria(j.categoria) for j in jogadores))

    grupos_por_categoria = defaultdict(list)
    for g in grupos:
        grupos_por_categoria[g.categoria].append(g)

    categorias_serializadas = []
    for categoria in categorias_set:
        grupos_cat = grupos_por_categoria.get(categoria, [])
        todos_fin_cat = bool(grupos_cat) and all(g.status == 'finalizado' for g in grupos_cat)

        mata_mata = None
        if tem_mata_mata:
            partidas_cat = (
                ChaveamentoPartida.query
                .filter_by(campeonato_id=campeonato_id, categoria=categoria)
                .order_by(ChaveamentoPartida.rodada.asc(), ChaveamentoPartida.posicao.asc())
                .all()
            )
            if partidas_cat:
                total_rodadas = max(p.rodada for p in partidas_cat)
                rodadas_dict = defaultdict(list)
                for p in partidas_cat:
                    rodadas_dict[p.rodada].append(p)
                rodadas = [
                    {
                        'numero': rn,
                        'nome': nome_rodada_por_numero(rn, total_rodadas),
                        'partidas': [_serializar_partida(p) for p in sorted(rodadas_dict[rn], key=lambda x: x.posicao)]
                    }
                    for rn in sorted(rodadas_dict.keys())
                ]
                jogadores_cat = [j for j in jogadores if normalizar_categoria(j.categoria) == categoria]
                final = next((p for p in partidas_cat if p.rodada == total_rodadas), None)
                mata_mata = {
                    'modo': 'vivo',
                    'total_jogadores': len(jogadores_cat),
                    'tamanho_chave': 2 ** total_rodadas,
                    'rodadas': rodadas,
                    'campeao': resumo_inscrito(final.vencedor) if final and final.vencedor else None,
                    'campeao_provisorio': None
                }

        categorias_serializadas.append({
            'categoria': categoria,
            'grupos': [_serializar_grupo(g) for g in grupos_cat],
            'todos_grupos_finalizados': todos_fin_cat,
            'mata_mata': mata_mata
        })

    return {
        'campeonato_id': campeonato_id,
        'formato': 'grupos_eliminacao' if tem_grupos else 'eliminacao_simples',
        'fase_atual': fase_atual,
        'tem_grupos': tem_grupos,
        'tem_mata_mata': tem_mata_mata,
        'todos_grupos_finalizados': todos_grupos_finalizados,
        'categorias': categorias_serializadas
    }