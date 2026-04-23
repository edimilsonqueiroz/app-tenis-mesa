"""
Testes para as rotas de placar
"""
import pytest
import json


class TestPlacarRoutes:
    """Testa rotas de placar"""
    
    def test_obter_placar(self, client, mesa):
        """Testa obtenção de placar"""
        response = client.get(f'/api/placar/mesa/{mesa.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['pontos_time1'] == 0
        assert data['pontos_time2'] == 0
        assert data['set_numero'] == 1
    
    def test_obter_placar_mesa_inexistente(self, client):
        """Testa obtenção de placar para mesa inexistente"""
        response = client.get('/api/placar/mesa/99999')
        assert response.status_code == 404
    
    def test_adicionar_ponto_time1(self, client, mesa_com_jogadores):
        """Testa adição de ponto para time 1"""
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/adicionar-ponto',
            json={'time': 1}
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        placar_data = data.get('placar') or data
        assert placar_data['pontos_time1'] == 1
        assert placar_data['pontos_time2'] == 0
    
    def test_adicionar_ponto_time2(self, client, mesa_com_jogadores):
        """Testa adição de ponto para time 2"""
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/adicionar-ponto',
            json={'time': 2}
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['placar']['pontos_time1'] == 0
        assert data['placar']['pontos_time2'] == 1
    
    def test_adicionar_multiplos_pontos(self, client, mesa_com_jogadores):
        """Testa adição de múltiplos pontos"""
        # Adicionar 5 pontos para time 1
        for _ in range(5):
            client.post(
                f'/api/placar/mesa/{mesa_com_jogadores.id}/adicionar-ponto',
                json={'time': 1}
            )
        
        response = client.get(f'/api/placar/mesa/{mesa_com_jogadores.id}')
        data = json.loads(response.data)
        assert data['pontos_time1'] == 5
    
    def test_remover_ponto(self, client, mesa_com_jogadores):
        """Testa remoção de ponto"""
        # Adicionar ponto
        client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/adicionar-ponto',
            json={'time': 1}
        )
        
        # Remover ponto
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/remover-ponto',
            json={'time': 1}
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['placar']['pontos_time1'] == 0
    
    def test_remover_ponto_zero(self, client, mesa_com_jogadores):
        """Testa que não pode remover ponto negativo"""
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/remover-ponto',
            json={'time': 1}
        )
        # Deve falhar ou manter em 0
        data = json.loads(response.data)
        assert data['placar']['pontos_time1'] >= 0
    
    def test_set_pontos(self, client, mesa_com_jogadores):
        """Testa definição manual de pontos"""
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/set-pontos',
            json={'pontos_time1': 10, 'pontos_time2': 8}
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['pontos_time1'] == 10
        assert data['pontos_time2'] == 8
    
    def test_trocar_sacador(self, client, mesa_com_jogadores):
        """Testa troca de sacador"""
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/trocar-sacador',
            json={}
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['placar']['servidor_time'] == 2
    
    def test_trocar_sacador_alternancia(self, client, mesa_com_jogadores):
        """Testa alternância de sacador"""
        # Trocar para time 2
        client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/trocar-sacador',
            json={}
        )
        
        # Trocar para time 1
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/trocar-sacador',
            json={}
        )
        
        data = json.loads(response.data)
        assert data['placar']['servidor_time'] == 1
    
    def test_reset_mesa(self, client, mesa_com_jogadores):
        """Testa reset da mesa"""
        # Adicionar alguns pontos
        for _ in range(5):
            client.post(
                f'/api/placar/mesa/{mesa_com_jogadores.id}/adicionar-ponto',
                json={'time': 1}
            )
        
        # Reset
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/reset',
            json={}
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['placar']['pontos_time1'] == 0
        assert data['placar']['pontos_time2'] == 0
        assert data['placar']['set_numero'] == 1
    
    def test_reset_mesa_muda_status(self, client, mesa_com_jogadores):
        """Testa que reset muda status para disponível"""
        # Verificar que status é em_uso
        from models import Mesa, db
        mesa = Mesa.query.get(mesa_com_jogadores.id)
        assert mesa.status == 'em_uso'
        
        # Reset
        client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/reset',
            json={}
        )
        
        # Verificar que status mudou para disponível
        db.session.refresh(mesa)
        assert mesa.status == 'disponivel'
    
    def test_configurar_formato_melhor_de_3(self, client, mesa_com_jogadores):
        """Testa configuração de formato do jogo"""
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/configurar-formato',
            json={'formato_jogo': 'melhor_de_3'}
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['placar']['formato_jogo'] == 'melhor_de_3'
    
    def test_configurar_formato_melhor_de_5(self, client, mesa_com_jogadores):
        """Testa configuração de formato melhor de 5"""
        response = client.post(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/configurar-formato',
            json={'formato_jogo': 'melhor_de_5'}
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['placar']['formato_jogo'] == 'melhor_de_5'
    
    def test_obter_formatos(self, client, mesa_com_jogadores):
        """Testa obtenção de formatos disponíveis"""
        response = client.get(
            f'/api/placar/mesa/{mesa_com_jogadores.id}/obter-formatos'
        )
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'formatos_disponiveis' in data
        assert 'melhor_de_3' in data['formatos_disponiveis']
        assert 'melhor_de_5' in data['formatos_disponiveis']
