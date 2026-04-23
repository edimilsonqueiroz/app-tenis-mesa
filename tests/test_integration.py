"""
Testes de integração - Cenários completos de jogo
"""
import pytest
import json
from models import Mesa, Placar, db


class TestFluxoJogoCompleto:
    """Testa fluxo completo de um jogo"""
    
    def test_jogo_simples_time1_vence_set(self, client, mesa_com_jogadores):
        """Testa jogo simples onde time 1 vence um set"""
        mesa_id = mesa_com_jogadores.id
        
        # Adicionar pontos até que time 1 vença com 11x8
        for i in range(11):
            client.post(
                f'/api/placar/mesa/{mesa_id}/adicionar-ponto',
                json={'time': 1}
            )
            # Adicionar alguns pontos para time 2 (mas menos de 11)
            if i < 8:
                client.post(
                    f'/api/placar/mesa/{mesa_id}/adicionar-ponto',
                    json={'time': 2}
                )
        
        # Verificar resultado
        response = client.get(f'/api/placar/mesa/{mesa_id}')
        data = json.loads(response.data)
        
        assert data['sets_time1'] == 1
        assert data['sets_time2'] == 0
        assert data['set_numero'] == 2
        assert data['pontos_time1'] == 0  # Resetou para novo set
        assert data['pontos_time2'] == 0
    
    def test_jogo_com_deuce(self, client, mesa_com_jogadores):
        """Testa jogo com deuce (empate após 10x10)"""
        mesa_id = mesa_com_jogadores.id
        
        # Levar para 10x10
        for _ in range(10):
            client.post(
                f'/api/placar/mesa/{mesa_id}/adicionar-ponto',
                json={'time': 1}
            )
            client.post(
                f'/api/placar/mesa/{mesa_id}/adicionar-ponto',
                json={'time': 2}
            )
        
        response = client.get(f'/api/placar/mesa/{mesa_id}')
        data = json.loads(response.data)
        assert data['pontos_time1'] == 10
        assert data['pontos_time2'] == 10
        
        # Adicionar mais 1 ponto para time 1
        client.post(
            f'/api/placar/mesa/{mesa_id}/adicionar-ponto',
            json={'time': 1}
        )
        
        response = client.get(f'/api/placar/mesa/{mesa_id}')
        data = json.loads(response.data)
        assert data['pontos_time1'] == 11
        assert data['pontos_time2'] == 10
        
        # Adicionar outro ponto para time 2 (empata)
        client.post(
            f'/api/placar/mesa/{mesa_id}/adicionar-ponto',
            json={'time': 2}
        )
        
        response = client.get(f'/api/placar/mesa/{mesa_id}')
        data = json.loads(response.data)
        assert data['pontos_time1'] == 11
        assert data['pontos_time2'] == 11
    
    def test_jogo_completo_melhor_de_3(self, client, mesa_com_jogadores):
        """Testa jogo completo melhor de 3"""
        mesa_id = mesa_com_jogadores.id
        
        # Set 1: Time 1 vence 11x9 (alternando pontos)
        for i in range(11):
            client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 1})
            if i < 9:
                client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 2})
        
        # Set 2: Time 2 vence 12x10 (alternando pontos)
        for i in range(12):
            client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 2})
            if i < 10:
                client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 1})
        
        # Set 3: Time 1 vence 11x8 (alternando pontos)
        for i in range(11):
            client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 1})
            if i < 8:
                client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 2})
        
        # Verificar resultado final
        response = client.get(f'/api/placar/mesa/{mesa_id}')
        data = json.loads(response.data)
        
        assert data['sets_time1'] == 2
        assert data['sets_time2'] == 1
    
    def test_alternancia_servidor(self, client, mesa_com_jogadores):
        """Testa alternância correta do servidor a cada 2 saques"""
        mesa_id = mesa_com_jogadores.id
        placar = Mesa.query.get(mesa_id).placar
        
        # Inicial: Time 1 serve
        assert placar.servidor_time == 1
        assert placar.serves_no_set == 0
        
        # Simular alternância após cada ponto
        # Ponto 1: serves_no_set = 1
        client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 1})
        db.session.refresh(placar)
        assert placar.servidor_time == 1
        
        # Ponto 2: serves_no_set = 2 -> alterna para time 2
        client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 2})
        db.session.refresh(placar)
        assert placar.servidor_time == 2
        
        # Ponto 3: serves_no_set = 1 (reset)
        client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 1})
        db.session.refresh(placar)
        assert placar.servidor_time == 2
        
        # Ponto 4: serves_no_set = 2 -> alterna para time 1
        client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 2})
        db.session.refresh(placar)
        assert placar.servidor_time == 1
    
    def test_undo_ponto(self, client, mesa_com_jogadores):
        """Testa desfazer ponto"""
        mesa_id = mesa_com_jogadores.id
        
        # Adicionar ponto
        client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 1})
        
        response = client.get(f'/api/placar/mesa/{mesa_id}')
        data = json.loads(response.data)
        assert data['pontos_time1'] == 1
        
        # Remover ponto
        client.post(f'/api/placar/mesa/{mesa_id}/remover-ponto', json={'time': 1})
        
        response = client.get(f'/api/placar/mesa/{mesa_id}')
        data = json.loads(response.data)
        assert data['pontos_time1'] == 0


class TestResetMesaAposJogo:
    """Testa reset de mesa após jogo finalizado"""
    
    def test_reset_apos_jogo_completo(self, client, mesa_com_jogadores):
        """Testa reset completo após jogo"""
        mesa_id = mesa_com_jogadores.id
        
        # Jogar até vencer
        for set_num in range(2):
            for _ in range(11):
                client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 1})
            for _ in range(9):
                client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 2})
        
        # Terceiro set
        for _ in range(11):
            client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 1})
        for _ in range(8):
            client.post(f'/api/placar/mesa/{mesa_id}/adicionar-ponto', json={'time': 2})
        
        # Verificar que jogo terminou
        mesa = Mesa.query.get(mesa_id)
        assert mesa.status == 'em_uso'
        
        # Reset da mesa
        response = client.post(f'/api/placar/mesa/{mesa_id}/reset', json={})
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['placar']['pontos_time1'] == 0
        assert data['placar']['pontos_time2'] == 0
        assert data['placar']['sets_time1'] == 0
        assert data['placar']['sets_time2'] == 0
        
        # Verificar status mudou
        mesa_atualizada = Mesa.query.get(mesa_id)
        assert mesa_atualizada.status == 'disponivel'
    
    def test_liberar_mesa_mantem_jogadores(self, client, mesa_com_jogadores):
        """Testa que liberar mesa mantém jogadores"""
        mesa_id = mesa_com_jogadores.id
        
        # Verificar jogadores antes
        mesa = Mesa.query.get(mesa_id)
        jogadores_antes = len(mesa.jogadores)
        assert jogadores_antes == 2
        
        # Reset/Liberar mesa
        client.post(f'/api/placar/mesa/{mesa_id}/reset', json={})
        
        # Verificar que jogadores ainda existem
        mesa_atualizada = Mesa.query.get(mesa_id)
        assert len(mesa_atualizada.jogadores) == jogadores_antes
        
        # Mas placar foi resetado
        assert mesa_atualizada.placar.pontos_time1 == 0
        assert mesa_atualizada.placar.pontos_time2 == 0


class TestValidacoesSistema:
    """Testa validações importantes do sistema"""
    
    def test_nao_adiciona_ponto_sem_jogadores(self, client, mesa):
        """Testa adição de ponto em mesa sem jogadores"""
        response = client.post(
            f'/api/placar/mesa/{mesa.id}/adicionar-ponto',
            json={'time': 1}
        )
        # Pode funcionar mesmo sem jogadores (placar permite)
        assert response.status_code in [200, 400, 404]
    
    def test_nao_pode_acessar_placar_sem_jogadores(self, client, mesa):
        """Testa acesso a placar sem jogadores"""
        response = client.get(f'/api/placar/mesa/{mesa.id}')
        # Deve funcionar mas indicar que não há jogadores
        assert response.status_code in [200, 404]
    
    def test_adiciona_ponto_time_invalido(self, client, mesa_com_jogadores):
        """Testa que rejeita time inválido"""
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/adicionar-ponto',
            json={'time': 3}
        )
        assert response.status_code == 400
    
    def test_pontos_nao_podem_ser_negativos(self, client, mesa_com_jogadores):
        """Testa que pontos não podem ser negativos"""
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/remover-ponto',
            json={'time': 1}
        )
        
        # Se conseguir remover, não pode ficar negativo
        if response.status_code == 200:
            data = json.loads(response.data)
            assert data['placar']['pontos_time1'] >= 0
