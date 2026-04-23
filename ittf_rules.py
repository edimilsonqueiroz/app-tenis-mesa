"""
Módulo de validação de regras ITTF (Federação Internacional de Tênis de Mesa)

Este módulo implementa as regras oficiais de pontuação, incluindo:
- Pontuação até 11 pontos com diferença mínima de 2 pontos
- Rotação de sacador a cada 2 saques
- Controle de sets
"""


def validar_ponto_ittf(pontos_time1, pontos_time2):
    """
    Valida se um set deve ser terminado de acordo com regras ITTF.
    
    Regras:
    - Primeiro time a atingir 11 pontos COM diferença de 2+ pontos vence o set
    - Exemplo: 11-9 = time 1 vence
    - Exemplo: 11-10 não termina, continua
    - Exemplo: 12-10 = time 2 vence (após empate em 10-10)
    
    Args:
        pontos_time1: Pontos do time 1
        pontos_time2: Pontos do time 2
    
    Returns:
        dict com:
        - 'set_terminado': bool
        - 'vencedor': 1, 2, ou None
        - 'razao': string descritiva
    """
    
    # Verifica se algum time tem 11+ pontos
    if pontos_time1 >= 11 or pontos_time2 >= 11:
        diferenca = abs(pontos_time1 - pontos_time2)
        
        # Diferença de 2+ pontos = set terminado
        if diferenca >= 2:
            vencedor = 1 if pontos_time1 > pontos_time2 else 2
            return {
                'set_terminado': True,
                'vencedor': vencedor,
                'razao': f"Time {vencedor} atingiu {max(pontos_time1, pontos_time2)} pontos com {diferenca} de diferença"
            }
    
    return {
        'set_terminado': False,
        'vencedor': None,
        'razao': None
    }


def proximo_servidor(servidor_atual, serves_no_set, pontos_time1=0, pontos_time2=0):
    """
    Determina qual time deve sacar a seguir baseado nas regras ITTF.
    
    Regras:
    - Cada jogador saca 2 vezes consecutivas
    - Após 2 saques, passa para o outro time
    - Exceção: em deuce (pontos >= 10 e iguais ou apenas 1 ponto de diferença),
      o saque alterna a cada ponto
    
    Args:
        servidor_atual: Time que está sacando (1 ou 2)
        serves_no_set: Número de saques consecutivos (0, 1, 2, ...)
        pontos_time1: Pontos do time 1 (opcional, para detectar deuce)
        pontos_time2: Pontos do time 2 (opcional, para detectar deuce)
    
    Returns:
        dict com:
        - 'proximo_servidor': int (1 ou 2)
        - 'novo_serves': int (contador para o novo servidor)
        - 'troca_servidor': bool
        - 'em_deuce': bool
    """
    
    # Detecta deuce: ambos têm 10+ e diferença <= 1
    em_deuce = (pontos_time1 >= 10 and pontos_time2 >= 10 and 
                abs(pontos_time1 - pontos_time2) <= 1)
    
    if em_deuce:
        # Em deuce, o saque alterna a cada ponto
        proximo = 2 if servidor_atual == 1 else 1
        novo_serves = 0
        troca = True
    else:
        # Em situação normal, troca a cada 2 saques
        novo_serves = (serves_no_set + 1) % 2
        
        if novo_serves == 0:
            # Completou 2 saques, troca de servidor
            proximo = 2 if servidor_atual == 1 else 1
            troca = True
        else:
            # Continua com o mesmo servidor
            proximo = servidor_atual
            troca = False
    
    return {
        'proximo_servidor': proximo,
        'novo_serves': novo_serves,
        'troca_servidor': troca,
        'em_deuce': em_deuce
    }


def proximo_set(sets_time1, sets_time2, vencedor_set, formato_jogo='melhor_de_3'):
    """
    Valida se o jogo deve continuar ou se foi finalizado.
    
    Suporta melhor de 3 sets (primeiro a vencer 2), melhor de 5 sets (primeiro a vencer 3)
    e melhor de 7 sets (primeiro a vencer 4).
    
    Regras ITTF:
    - Time a atingir o número necessário de sets vence
    - No set 3+ (melhor de 5), o time que sacou primeiro muda a cada set
    
    Args:
        sets_time1: Sets ganhos pelo time 1
        sets_time2: Sets ganhos pelo time 2
        vencedor_set: Time que venceu o set anterior (1 ou 2)
        formato_jogo: 'melhor_de_3' (padrão), 'melhor_de_5' ou 'melhor_de_7'
    
    Returns:
        dict com:
        - 'novo_set': int (número do próximo set) ou None se jogo finalizado
        - 'jogo_finalizado': bool
        - 'vencedor_jogo': 1, 2, ou None
        - 'razao': string descritiva
        - 'sets_time1': Sets ganhos pelo time 1 após este set
        - 'sets_time2': Sets ganhos pelo time 2 após este set
    """
    
    # Atualiza sets ganhos
    novo_sets_time1 = sets_time1 + (1 if vencedor_set == 1 else 0)
    novo_sets_time2 = sets_time2 + (1 if vencedor_set == 2 else 0)
    
    # Define quantos sets são necessários para vencer
    sets_para_vencer_map = {
        'melhor_de_3': 2,
        'melhor_de_5': 3,
        'melhor_de_7': 4
    }
    
    sets_para_vencer = sets_para_vencer_map.get(formato_jogo, 2)
    
    # Verifica se algum time alcançou o número de sets necessário
    if novo_sets_time1 >= sets_para_vencer:
        return {
            'novo_set': None,
            'jogo_finalizado': True,
            'vencedor_jogo': 1,
            'razao': f"Time 1 venceu o jogo ({novo_sets_time1} x {novo_sets_time2} sets)",
            'sets_time1': novo_sets_time1,
            'sets_time2': novo_sets_time2
        }
    elif novo_sets_time2 >= sets_para_vencer:
        return {
            'novo_set': None,
            'jogo_finalizado': True,
            'vencedor_jogo': 2,
            'razao': f"Time 2 venceu o jogo ({novo_sets_time2} x {novo_sets_time1} sets)",
            'sets_time1': novo_sets_time1,
            'sets_time2': novo_sets_time2
        }
    else:
        # Jogo continua com próximo set
        novo_set_numero = novo_sets_time1 + novo_sets_time2 + 1
        return {
            'novo_set': novo_set_numero,
            'jogo_finalizado': False,
            'vencedor_jogo': None,
            'razao': f"Próximo set (Set {novo_set_numero})",
            'sets_time1': novo_sets_time1,
            'sets_time2': novo_sets_time2
        }


def servidor_proximo_set(set_numero, servidor_comecou_set_1):
    """
    Determina qual time deve sacar no próximo set de acordo com regras ITTF.
    
    Regras ITTF:
    - Time que saca primeiro no Set 1 não saca primeiro no Set 2
    - Essa alternância continua em sets subsequentes
    - Quem saca SEGUNDO no Set 1 saca PRIMEIRO no Set 2
    - Quem saca PRIMEIRO no Set 1 saca SEGUNDO no Set 2
    
    Args:
        set_numero: Número do próximo set (2, 3, 4, ...)
        servidor_comecou_set_1: Time que começou sacando no Set 1 (1 ou 2)
    
    Returns:
        int: Time que deve sacar primeiro no próximo set (1 ou 2)
    """
    
    if set_numero == 2:
        # Set 2: alterna de quem começou no Set 1
        return 2 if servidor_comecou_set_1 == 1 else 1
    else:
        # Sets 3+: padrão é seguir a mesma alternância do Set 2
        # Se foi 2 no Set 2, segue 2, 1, 2, 1...
        # Se foi 1 no Set 2, segue 1, 2, 1, 2...
        set_2_servidor = 2 if servidor_comecou_set_1 == 1 else 1
        
        # Conta quantos sets passaram desde o Set 2
        sets_from_2 = set_numero - 2
        
        # Se é par (impares de distância do Set 2), same as Set 2
        # Se é ímpar (pares de distância do Set 2), oposto do Set 2
        if sets_from_2 % 2 == 0:
            return set_2_servidor
        else:
            return 2 if set_2_servidor == 1 else 1


def gerar_status_jogo(placar_obj):
    """
    Gera um resumo do status atual do jogo com informações ITTF.
    
    Args:
        placar_obj: Objeto Placar do banco de dados
    
    Returns:
        dict com todas as informações formatadas do jogo
    """
    
    validacao = validar_ponto_ittf(placar_obj.pontos_time1, placar_obj.pontos_time2)
    proximo_serv = proximo_servidor(placar_obj.servidor_time, placar_obj.serves_no_set,
                                   placar_obj.pontos_time1, placar_obj.pontos_time2)
    
    return {
        'pontos': {
            'time1': placar_obj.pontos_time1,
            'time2': placar_obj.pontos_time2
        },
        'sets': {
            'time1': placar_obj.sets_time1,
            'time2': placar_obj.sets_time2,
            'numero_atual': placar_obj.set_numero
        },
        'servidor': {
            'time_atual': placar_obj.servidor_time,
            'proximo_time': proximo_serv['proximo_servidor'],
            'serves_consecutivos': placar_obj.serves_no_set,
            'texto': f"Time {placar_obj.servidor_time} sacando"
        },
        'validacao': validacao,
        'status': placar_obj.status
    }
