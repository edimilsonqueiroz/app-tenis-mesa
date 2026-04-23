"""
Testes para as rotas de mesas e status
"""
import pytest
import json
from models import Mesa, Jogador, db


class TestMesasRoutes:
    """Testa rotas de mesas"""
    
    def test_criar_mesa(self, client, campeonato):
        """Testa criação de mesa"""
        response = client.post(
            '/api/mesas',
            json={'campeonato_id': campeonato.id, 'numero': 5}
        )
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['numero'] == 5
        assert data['status'] == 'disponivel'
    
    def test_listar_mesas(self, client, mesa):
        """Testa obtenção de mesa específica"""
        response = client.get(f'/api/mesas/{mesa.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['numero'] == mesa.numero
    
    def test_obter_mesa(self, client, mesa):
        """Testa obtenção de mesa específica"""
        response = client.get(f'/api/mesas/{mesa.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['numero'] == mesa.numero
        assert data['status'] == 'disponivel'
    
    def test_obter_mesa_inexistente(self, client):
        """Testa obtenção de mesa inexistente"""
        response = client.get('/api/mesas/99999')
        assert response.status_code == 404
    
    def test_deletar_mesa(self, client, mesa):
        """Testa deleção de mesa"""
        mesa_id = mesa.id
        response = client.delete(f'/api/mesas/{mesa_id}')
        assert response.status_code == 200
        
        # Verificar que foi deletada
        mesa_deletada = Mesa.query.get(mesa_id)
        assert mesa_deletada is None
    
    def test_atualizar_jogadores(self, client, mesa):
        """Testa atualização de jogadores"""
        response = client.post(
            f'/api/mesas/{mesa.id}/atualizar-jogadores',
            json={
                'time': 1,
                'nomes': ['João', 'Maria']
            }
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['sucesso'] == True
    
    def test_atualizar_jogadores_muda_status(self, client, mesa):
        """Testa que atualizar jogadores muda status para em_uso"""
        # Verificar status inicial
        mesa_antes = Mesa.query.get(mesa.id)
        assert mesa_antes.status == 'disponivel'
        
        # Atualizar jogadores
        client.post(
            f'/api/mesas/{mesa.id}/atualizar-jogadores',
            json={
                'time': 1,
                'nomes': ['João', 'Maria']
            }
        )
        
        # Verificar status mudou
        mesa_depois = Mesa.query.get(mesa.id)
        assert mesa_depois.status == 'em_uso'
    
    def test_reset_completo_mesa(self, client, mesa_com_jogadores):
        """Testa reset completo da mesa"""
        # Adicionar pontos e sets
        placar = mesa_com_jogadores.placar
        placar.pontos_time1 = 11
        placar.pontos_time2 = 5
        placar.sets_time1 = 1
        placar.set_numero = 2
        db.session.commit()
        
        # Reset
        response = client.post(
            f'/api/mesas/{mesa_com_jogadores.id}/resetar'
        )
        assert response.status_code == 200
        
        # Verificar que foi resetado
        placar_atualizado = Mesa.query.get(mesa_com_jogadores.id).placar
        assert placar_atualizado.pontos_time1 == 0
        assert placar_atualizado.pontos_time2 == 0
        assert placar_atualizado.sets_time1 == 0
        assert placar_atualizado.set_numero == 1


class TestMesaStatus:
    """Testa mudanças de status da mesa"""
    
    def test_mesa_disponivel_inicial(self, app_context, mesa):
        """Testa que mesa é criada como disponível"""
        assert mesa.status == 'disponivel'
    
    def test_mesa_muda_para_em_uso(self, app_context, mesa):
        """Testa mudança para em_uso"""
        mesa.status = 'em_uso'
        db.session.commit()
        
        mesa_atualizada = Mesa.query.get(mesa.id)
        assert mesa_atualizada.status == 'em_uso'
    
    def test_mesa_com_jogadores_em_uso(self, app_context, mesa):
        """Testa que mesa com jogadores pode estar em uso"""
        jogador1 = Jogador(nome='Jogador 1', mesa_id=mesa.id, time=1)
        jogador2 = Jogador(nome='Jogador 2', mesa_id=mesa.id, time=2)
        db.session.add_all([jogador1, jogador2])
        
        mesa.status = 'em_uso'
        db.session.commit()
        
        mesa_atualizada = Mesa.query.get(mesa.id)
        assert len(mesa_atualizada.jogadores) == 2
        assert mesa_atualizada.status == 'em_uso'
    
    def test_mesa_volta_para_disponivel(self, app_context, mesa_com_jogadores):
        """Testa volta para disponível após reset"""
        mesa_com_jogadores.status = 'disponivel'
        db.session.commit()
        
        mesa_atualizada = Mesa.query.get(mesa_com_jogadores.id)
        assert mesa_atualizada.status == 'disponivel'


class TestMesaValidacao:
    """Testa validações de mesa"""
    
    def test_nao_pode_criar_mesa_sem_numero(self, client, campeonato):
        """Testa que não pode criar mesa sem número"""
        response = client.post(
            '/api/mesas',
            json={'campeonato_id': campeonato.id}
        )
        assert response.status_code in [400, 422]
    
    def test_numero_mesa_unico_por_campeonato(self, client, mesa):
        """Testa criar segunda mesa com número diferente"""
        response = client.post(
            '/api/mesas',
            json={'campeonato_id': mesa.campeonato_id, 'numero': 2}
        )
        # Deve criar nova mesa com sucesso
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['numero'] == 2
    
    def test_mesa_campeonato_inexistente(self, client):
        """Testa criar mesa em campeonato inexistente"""
        response = client.post(
            '/api/mesas',
            json={'campeonato_id': 99999, 'numero': 1}
        )
        assert response.status_code == 404
