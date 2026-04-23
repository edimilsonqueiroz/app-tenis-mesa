from flask import Blueprint, request, jsonify
from chaveamento import registrar_resultado_por_mesa
from models import db, Placar, Mesa, ResultadoPartida
from ittf_rules import validar_ponto_ittf, proximo_servidor, proximo_set, gerar_status_jogo, servidor_proximo_set

bp = Blueprint('placar', __name__, url_prefix='/api/placar')


def mesa_esta_pausada(mesa):
    """Retorna True quando a mesa/placar está pausada e não pode alterar pontos."""
    if not mesa or not mesa.placar:
        return False
    return mesa.status == 'pausada' or mesa.placar.status == 'pausado'

def broadcast_placar_update(mesa_id, placar_data):
    """Envia atualização de placar para todos os clientes inscritos na mesa"""
    try:
        from app import socketio
        room = f'mesa_{mesa_id}'
        socketio.emit('placar_atualizado', {
            'mesa_id': mesa_id,
            'placar': placar_data
        }, room=room)
        print(f"[BROADCAST] Atualização enviada para mesa {mesa_id}")
    except Exception as e:
        print(f"[BROADCAST ERROR] Erro ao enviar atualização: {e}")

@bp.route('/mesa/<int:mesa_id>', methods=['GET'])
def obter_placar(mesa_id):
    """Obtém o placar de uma mesa"""
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404
    
    return jsonify(mesa.placar.to_dict())

@bp.route('/mesa/<int:mesa_id>/adicionar-ponto', methods=['POST'])
def adicionar_ponto(mesa_id):
    """
    Adiciona ponto para um time e aplica regras ITTF automaticamente.
    
    Regras ITTF aplicadas:
    - Termina o set quando um time atinge 11+ pontos com 2+ de diferença
    - Alterna o sacador a cada 2 saques
    - Avança automaticamente para o próximo set
    - Finaliza o jogo quando um time vence 2 sets
    """
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404

    if mesa_esta_pausada(mesa):
        return jsonify({'erro': 'Mesa em pausa. Não é permitido alterar pontos.'}), 409
    
    dados = request.get_json()
    
    if 'time' not in dados or dados['time'] not in [1, 2]:
        return jsonify({'erro': 'time inválido (deve ser 1 ou 2)'}), 400
    
    try:
        placar = mesa.placar
        time_ponto = dados['time']
        
        # Adiciona o ponto
        if time_ponto == 1:
            placar.pontos_time1 += 1
        else:
            placar.pontos_time2 += 1
        
        # Contabiliza pontos marcados para cada jogador do time que marcou
        for jogador_mesa in mesa.jogadores_mesa:
            if jogador_mesa.time == time_ponto:
                jogador_mesa.pontos_marcados += 1
        
        # Valida se o set deve acabar
        validacao = validar_ponto_ittf(placar.pontos_time1, placar.pontos_time2)
        
        resposta = {
            'placar': placar.to_dict(),
            'ittf_info': gerar_status_jogo(placar)
        }
        
        if validacao['set_terminado']:
            vencedor_set = validacao['vencedor']
            
            # Calcula o resultado e incrementa os sets automaticamente
            result_jogo = proximo_set(placar.sets_time1, placar.sets_time2, vencedor_set, placar.formato_jogo)
            
            # Atualiza sets ganhos com os valores calculados por proximo_set
            placar.sets_time1 = result_jogo['sets_time1']
            placar.sets_time2 = result_jogo['sets_time2']
            
            # Contabiliza sets vencidos para cada jogador do time vencedor
            for jogador_mesa in mesa.jogadores_mesa:
                if jogador_mesa.time == vencedor_set:
                    jogador_mesa.sets_vencidos += 1
                    print(f"[SET CONTABILIZADO] Jogador {jogador_mesa.jogador.nome} (Time {vencedor_set}) venceu um set. Total: {jogador_mesa.sets_vencidos}")
            
            resposta['set_info'] = {
                'set_terminado': True,
                'vencedor': vencedor_set,
                'sets_time1': placar.sets_time1,
                'sets_time2': placar.sets_time2,
                'razao': validacao['razao']
            }
            
            if result_jogo['jogo_finalizado']:
                # Jogo terminou! Um time venceu a maioria dos sets
                placar.status = 'finalizado'
                
                # Determinar qual jogador/time venceu mais sets
                vencedor_time = result_jogo['vencedor_jogo']
                jogadores_vencedores = [j for j in mesa.jogadores_mesa if j.time == vencedor_time]
                
                resposta['jogo_info'] = {
                    'jogo_finalizado': True,
                    'vencedor': vencedor_time,
                    'razao': result_jogo['razao'],
                    'sets_finais': {
                        'time1': placar.sets_time1,
                        'time2': placar.sets_time2
                    },
                    'jogadores_vencedores': [j.to_dict() for j in jogadores_vencedores]
                }

                partida_chaveamento = None
                tipo_resultado, partida_resultado = registrar_resultado_por_mesa(mesa, vencedor_time)
                if partida_resultado:
                    resposta['chaveamento_info'] = {
                        'tipo': tipo_resultado,
                        'partida_id': partida_resultado.id,
                        'categoria': partida_resultado.categoria,
                        'status': partida_resultado.status,
                        'vencedor_inscrito_id': partida_resultado.vencedor_inscrito_id
                    }
                    partida_chaveamento = partida_resultado
                
                print(f"[JOGO FINALIZADO] Time {vencedor_time} venceu com {placar.sets_time1} x {placar.sets_time2} sets")
            else:
                # Prepara próximo set automaticamente
                novo_set_numero = result_jogo['novo_set']
                placar.set_numero = novo_set_numero
                placar.pontos_time1 = 0
                placar.pontos_time2 = 0
                placar.serves_no_set = 0  # IMPORTANTE: Reseta saques para novo set
                
                # Determina o próximo servidor usando regras ITTF
                proximo_servidor_inicial = servidor_proximo_set(novo_set_numero, placar.servidor_inicial_jogo)
                placar.servidor_time = proximo_servidor_inicial

                # Se habilitado, troca os lados automaticamente ao iniciar novo set
                if placar.auto_troca_lados_set:
                    placar.lados_invertidos = not bool(placar.lados_invertidos)
                
                resposta['proximo_set'] = {
                    'set_numero': placar.set_numero,
                    'servidor_comeca': proximo_servidor_inicial,
                    'razao': result_jogo['razao'],
                    'sets_time1': placar.sets_time1,
                    'sets_time2': placar.sets_time2,
                    'pontos_resetados': True,
                    'serves_resetados': True,
                    'lados_invertidos': placar.lados_invertidos,
                    'troca_automatica_lados': bool(placar.auto_troca_lados_set)
                }
                
                print(f"[SET PRÓXIMO] Set {novo_set_numero} começando. Score: {placar.sets_time1} x {placar.sets_time2}. Servidor: Time {proximo_servidor_inicial}. Serves: 0")
        else:
            # Set continua, apenas atualiza servidor após cada ponto
            # IMPORTANTE: Incrementa o contador ANTES de verificar se troca
            placar.serves_no_set += 1
            
            # Verifica se deve trocar de servidor após cada 2 saques
            if placar.serves_no_set >= 2:
                # Troca de servidor
                placar.servidor_time = 2 if placar.servidor_time == 1 else 1
                placar.serves_no_set = 0
            
            print(f"[SAQUE] Time {placar.servidor_time}, Saque {placar.serves_no_set + 1}/2, Pontos: {placar.pontos_time1}x{placar.pontos_time2}")
        
        db.session.commit()
        
        # Broadcast da atualização para todos os clientes da mesa
        broadcast_placar_update(mesa_id, placar.to_dict())

        if resposta.get('jogo_info'):
            try:
                from app import broadcast_campeonato_update
                broadcast_campeonato_update(mesa.campeonato_id, 'chaveamento_atualizado')
            except Exception as e:
                print(f"[BROADCAST ERROR] Erro ao notificar chaveamento: {e}")
        
        return jsonify(resposta)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/mesa/<int:mesa_id>/remover-ponto', methods=['POST'])
def remover_ponto(mesa_id):
    """
    Remove ponto de um time, respeitando regras ITTF.
    
    Se um set estava finalizado, reverte para o estado anterior.
    """
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404

    if mesa_esta_pausada(mesa):
        return jsonify({'erro': 'Mesa em pausa. Não é permitido alterar pontos.'}), 409
    
    dados = request.get_json()
    
    if 'time' not in dados or dados['time'] not in [1, 2]:
        return jsonify({'erro': 'time inválido (deve ser 1 ou 2)'}), 400
    
    try:
        placar = mesa.placar
        time_remove = dados['time']
        
        # Verifica se estava no final do set antes de remover
        pontos_antigos_t1 = placar.pontos_time1
        pontos_antigos_t2 = placar.pontos_time2
        validacao_antes = validar_ponto_ittf(pontos_antigos_t1, pontos_antigos_t2)
        
        # Remove ponto
        if time_remove == 1:
            if placar.pontos_time1 > 0:
                placar.pontos_time1 -= 1
                # Decrementa pontos marcados dos jogadores do time
                for jogador_mesa in mesa.jogadores_mesa:
                    if jogador_mesa.time == time_remove and jogador_mesa.pontos_marcados > 0:
                        jogador_mesa.pontos_marcados -= 1
        else:
            if placar.pontos_time2 > 0:
                placar.pontos_time2 -= 1
                # Decrementa pontos marcados dos jogadores do time
                for jogador_mesa in mesa.jogadores_mesa:
                    if jogador_mesa.time == time_remove and jogador_mesa.pontos_marcados > 0:
                        jogador_mesa.pontos_marcados -= 1
        
        resposta = {
            'placar': placar.to_dict(),
            'ittf_info': gerar_status_jogo(placar)
        }
        
        # Se o set estava finalizado antes de remover, volta para em andamento
        if validacao_antes['set_terminado']:
            resposta['info'] = 'Set que estava finalizado agora continua'
        
        db.session.commit()
        
        # Broadcast da atualização para todos os clientes da mesa
        broadcast_placar_update(mesa_id, placar.to_dict())
        
        return jsonify(resposta)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/mesa/<int:mesa_id>/set-pontos', methods=['POST'])
def set_pontos(mesa_id):
    """Define os pontos diretamente"""
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404

    if mesa_esta_pausada(mesa):
        return jsonify({'erro': 'Mesa em pausa. Não é permitido alterar pontos.'}), 409
    
    dados = request.get_json()
    
    try:
        if 'pontos_time1' in dados:
            mesa.placar.pontos_time1 = max(0, int(dados['pontos_time1']))
        if 'pontos_time2' in dados:
            mesa.placar.pontos_time2 = max(0, int(dados['pontos_time2']))
        
        db.session.commit()
        
        # Broadcast da atualização para todos os clientes da mesa
        broadcast_placar_update(mesa_id, mesa.placar.to_dict())
        
        return jsonify(mesa.placar.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/mesa/<int:mesa_id>/status', methods=['POST'])
def atualizar_status_placar(mesa_id):
    """Atualiza o status do placar (em_andamento, pausado, finalizado)"""
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404
    
    dados = request.get_json()
    
    if 'status' not in dados:
        return jsonify({'erro': 'Status é obrigatório'}), 400
    
    try:
        mesa.placar.status = dados['status']
        db.session.commit()
        
        # Broadcast da atualização para todos os clientes da mesa
        broadcast_placar_update(mesa_id, mesa.placar.to_dict())
        
        return jsonify(mesa.placar.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/mesa/<int:mesa_id>/configurar-formato', methods=['POST'])
def configurar_formato(mesa_id):
    """
    Configura o formato do jogo (melhor de 3, 5 ou 7 sets).
    
    Nota: Só pode ser alterado se o jogo ainda não começou (sets em 0-0).
    """
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404
    
    dados = request.get_json()
    
    if 'formato_jogo' not in dados:
        return jsonify({'erro': 'formato_jogo é obrigatório'}), 400
    
    formato = dados['formato_jogo']
    formatos_validos = ['melhor_de_3', 'melhor_de_5', 'melhor_de_7']
    
    if formato not in formatos_validos:
        return jsonify({
            'erro': f'Formato inválido. Opções: {", ".join(formatos_validos)}'
        }), 400
    
    try:
        placar = mesa.placar
        
        placar.formato_jogo = formato
        db.session.commit()
        
        # Broadcast da atualização para todos os clientes da mesa
        broadcast_placar_update(mesa_id, placar.to_dict())
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'Formato alterado para {formato}',
            'placar': placar.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/mesa/<int:mesa_id>/obter-formatos', methods=['GET'])
def obter_formatos(mesa_id):
    """Retorna os formatos de jogo disponíveis e o atual"""
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404
    
    formatos = {
        'melhor_de_3': {'nome': 'Melhor de 3 sets', 'descricao': 'Primeiro a vencer 2 sets'},
        'melhor_de_5': {'nome': 'Melhor de 5 sets', 'descricao': 'Primeiro a vencer 3 sets'},
        'melhor_de_7': {'nome': 'Melhor de 7 sets', 'descricao': 'Primeiro a vencer 4 sets'}
    }
    
    return jsonify({
        'formato_atual': mesa.placar.formato_jogo,
        'formatos_disponiveis': formatos,
        'pode_alterar': mesa.placar.sets_time1 == 0 and mesa.placar.sets_time2 == 0
    })

@bp.route('/mesa/<int:mesa_id>/trocar-sacador', methods=['POST'])
def trocar_sacador(mesa_id):
    """Alterna manualmente o sacador (útil para o controle remoto)"""
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404
    
    try:
        placar = mesa.placar
        
        # Alterna o sacador
        placar.servidor_time = 2 if placar.servidor_time == 1 else 1
        # Reseta o contador de saques para o novo servidor
        placar.serves_no_set = 0
        
        db.session.commit()
        
        # Broadcast da atualização para todos os clientes da mesa
        broadcast_placar_update(mesa_id, placar.to_dict())
        
        return jsonify({
            'sucesso': True,
            'mensagem': f'Sacador alterado para Time {placar.servidor_time}',
            'placar': placar.to_dict(),
            'ittf_info': gerar_status_jogo(placar)
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/mesa/<int:mesa_id>/trocar-lados', methods=['POST'])
def trocar_lados(mesa_id):
    """Alterna a exibição dos lados (time 1 <-> time 2) no placar/controle."""
    mesa = Mesa.query.get(mesa_id)

    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404

    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404

    try:
        placar = mesa.placar
        placar.lados_invertidos = not bool(placar.lados_invertidos)

        db.session.commit()

        # Broadcast da atualização para todos os clientes da mesa
        broadcast_placar_update(mesa_id, placar.to_dict())

        return jsonify({
            'sucesso': True,
            'mensagem': 'Lados invertidos' if placar.lados_invertidos else 'Lados normalizados',
            'placar': placar.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/mesa/<int:mesa_id>/toggle-auto-troca-lados', methods=['POST'])
def toggle_auto_troca_lados(mesa_id):
    """Ativa/desativa a troca automática de lados ao iniciar cada novo set."""
    mesa = Mesa.query.get(mesa_id)

    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404

    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404

    try:
        placar = mesa.placar
        placar.auto_troca_lados_set = not bool(placar.auto_troca_lados_set)

        db.session.commit()

        # Broadcast da atualização para todos os clientes da mesa
        broadcast_placar_update(mesa_id, placar.to_dict())

        return jsonify({
            'sucesso': True,
            'mensagem': 'Troca automática de lados ativada' if placar.auto_troca_lados_set else 'Troca automática de lados desativada',
            'placar': placar.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/mesa/<int:mesa_id>/reset', methods=['POST'])
def reset_mesa(mesa_id):
    """
    Reseta o placar da mesa para o estado inicial.
    Mantém os jogadores cadastrados.
    """
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404
    
    try:
        placar = mesa.placar
        
        # Reseta todos os pontos e sets
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
        
        # Muda o status da mesa para disponível
        mesa.status = 'disponivel'
        
        db.session.commit()
        
        # Broadcast da atualização para todos os clientes da mesa
        broadcast_placar_update(mesa_id, placar.to_dict())
        
        # Também emitir atualização para a sala do campeonato
        try:
            from app import socketio
            room_campeonato = f'campeonato_{mesa.campeonato_id}'
            socketio.emit('mesa_atualizada', {
                'mesa_id': mesa_id,
                'mesa': mesa.to_dict()
            }, room=room_campeonato)
            print(f"[BROADCAST] Atualização de mesa enviada para campeonato {mesa.campeonato_id}")
        except Exception as e:
            print(f"[BROADCAST ERROR] Erro ao enviar atualização da mesa: {e}")
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Mesa resetada com sucesso',
            'placar': placar.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/mesa/<int:mesa_id>/iniciar-jogo', methods=['POST'])
def iniciar_jogo(mesa_id):
    """
    Inicia um novo jogo, mudando a mesa para status 'em_uso'.
    Verifica se há jogadores cadastrados na mesa.
    """
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada'}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado'}), 404
    
    # Verifica se há pelo menos 2 jogadores (um por time)
    if len(mesa.jogadores_mesa) < 2:
        return jsonify({'erro': 'É necessário pelo menos 2 jogadores (um por time)'}), 400
    
    try:
        # Muda o status da mesa para em_uso
        mesa.status = 'em_uso'
        
        # Garante que o placar está pronto
        placar = mesa.placar
        placar.status = 'em_andamento'
        
        db.session.commit()
        
        # Broadcast da atualização
        broadcast_placar_update(mesa_id, placar.to_dict())
        
        # Atualizar status da mesa para quem está vendo os detalhes
        try:
            from app import socketio
            room_campeonato = f'campeonato_{mesa.campeonato_id}'
            socketio.emit('mesa_atualizada', {
                'mesa_id': mesa_id,
                'mesa': mesa.to_dict()
            }, room=room_campeonato)
        except Exception as e:
            print(f"[BROADCAST ERROR] Erro ao enviar atualização: {e}")
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Jogo iniciado com sucesso',
            'placar': placar.to_dict(),
            'mesa_status': mesa.status
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 400

@bp.route('/mesa/<int:mesa_id>/liberar', methods=['POST'])
def liberar_mesa(mesa_id):
    """
    Libera a mesa após fim de partida:
    1. Registra o resultado da partida no chaveamento
    2. Remove todos os jogadores da mesa
    3. Reseta o placar para estado inicial
    4. Muda o status da mesa para disponível
    
    Espera: { "vencedor_time": 1 ou 2 }
    """
    mesa = Mesa.query.get(mesa_id)
    
    if not mesa:
        return jsonify({'erro': 'Mesa não encontrada', 'sucesso': False}), 404
    
    if not mesa.placar:
        return jsonify({'erro': 'Placar não encontrado', 'sucesso': False}), 404
    
    dados = request.get_json()
    vencedor_time = dados.get('vencedor_time') if dados else None
    
    if vencedor_time not in [1, 2]:
        return jsonify({'erro': 'vencedor_time deve ser 1 ou 2', 'sucesso': False}), 400
    
    try:
        print(f"[LIBERAR MESA] Iniciando liberação da mesa {mesa_id}")
        
        # 1. Registrar resultado da partida
        tipo_resultado, partida_resultado = registrar_resultado_por_mesa(mesa, vencedor_time)
        if partida_resultado:
            print(f"[LIBERAR MESA] Resultado registrado: {tipo_resultado} - Partida {partida_resultado.id}")
        else:
            print(f"[LIBERAR MESA] Nenhuma partida de chaveamento encontrada para registrar resultado")
        
        # 2. Registrar resultado no histórico de partidas (para o ranking)
        placar = mesa.placar
        
        # Obter nomes dos jogadores antes de deletar
        jogadores_time1 = [j.jogador.nome for j in mesa.jogadores_mesa if j.time == 1]
        jogadores_time2 = [j.jogador.nome for j in mesa.jogadores_mesa if j.time == 2]
        
        resultado_partida = ResultadoPartida(
            mesa_id=mesa_id,
            campeonato_id=mesa.campeonato_id,
            jogadores_time1=' & '.join(jogadores_time1) if jogadores_time1 else 'Vazio',
            jogadores_time2=' & '.join(jogadores_time2) if jogadores_time2 else 'Vazio',
            pontos_time1=placar.pontos_time1,
            pontos_time2=placar.pontos_time2,
            sets_time1=placar.sets_time1,
            sets_time2=placar.sets_time2,
            vencedor_time=vencedor_time
        )
        db.session.add(resultado_partida)
        print(f"[LIBERAR MESA] Resultado registrado no histórico: {jogadores_time1} vs {jogadores_time2}")
        
        # 3. Remover todos os jogadores da mesa (apenas desvincular, não deletar)
        jogadores_removidos = []
        for jogador in mesa.jogadores:
            jogadores_removidos.append(jogador.nome)
            jogador.mesa_id = None  # Apenas desvincula da mesa, não deleta o registro
        
        print(f"[LIBERAR MESA] Jogadores desvinculados da mesa: {', '.join(jogadores_removidos) if jogadores_removidos else 'nenhum'}")
        
        # 4. Resetar o placar
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
        
        # 5. Muda o status da mesa para disponível
        mesa.status = 'disponivel'
        
        db.session.commit()
        
        print(f"[LIBERAR MESA] Mesa {mesa_id} liberada com sucesso")
        
        # Broadcast da atualização para todos os clientes da mesa
        broadcast_placar_update(mesa_id, placar.to_dict())
        
        # Também emitir atualização para a sala do campeonato
        try:
            from app import socketio
            room_campeonato = f'campeonato_{mesa.campeonato_id}'
            socketio.emit('mesa_atualizada', {
                'mesa_id': mesa_id,
                'mesa': mesa.to_dict()
            }, room=room_campeonato)
            print(f"[BROADCAST] Atualização de mesa liberada enviada para campeonato {mesa.campeonato_id}")
        except Exception as e:
            print(f"[BROADCAST ERROR] Erro ao enviar atualização da mesa: {e}")
        
        return jsonify({
            'sucesso': True,
            'mensagem': 'Mesa liberada com sucesso',
            'placar': placar.to_dict(),
            'jogadores_removidos': jogadores_removidos,
            'resultado_registrado': bool(partida_resultado)
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"[LIBERAR MESA ERROR] {str(e)}")
        return jsonify({'erro': str(e), 'sucesso': False}), 400
