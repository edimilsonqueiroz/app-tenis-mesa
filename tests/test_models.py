"""
Testes para os modelos
"""
import pytest
from models import Campeonato, Mesa, Placar, Jogador


class TestCampeonato:
    """Testa modelo Campeonato"""
    
    def test_criar_campeonato(self, app_context, campeonato):
        """Testa criação de campeonato"""
        assert campeonato.id is not None
        assert campeonato.nome == 'Teste'
        assert campeonato.descricao == 'Campeonato de teste'
    
    def test_campeonato_to_dict(self, app_context, campeonato):
        """Testa conversão para dicionário"""
        camp_dict = campeonato.to_dict()
        assert camp_dict['nome'] == 'Teste'
        assert camp_dict['descricao'] == 'Campeonato de teste'
        assert 'id' in camp_dict


class TestMesa:
    """Testa modelo Mesa"""
    
    def test_criar_mesa(self, app_context, mesa):
        """Testa criação de mesa"""
        assert mesa.id is not None
        assert mesa.numero == 1
        assert mesa.status == 'disponivel'
    
    def test_mesa_status_inicial(self, app_context, mesa):
        """Testa status inicial da mesa"""
        assert mesa.status == 'disponivel'
    
    def test_mesa_status_em_uso(self, app_context, mesa):
        """Testa mudança de status para em_uso"""
        mesa.status = 'em_uso'
        from models import db
        db.session.commit()
        
        mesa_atualizada = Mesa.query.get(mesa.id)
        assert mesa_atualizada.status == 'em_uso'
    
    def test_mesa_tem_placar(self, app_context, mesa):
        """Testa que mesa possui placar"""
        assert mesa.placar is not None
        assert isinstance(mesa.placar, Placar)
    
    def test_mesa_to_dict(self, app_context, mesa):
        """Testa conversão para dicionário"""
        mesa_dict = mesa.to_dict()
        assert mesa_dict['numero'] == 1
        assert mesa_dict['status'] == 'disponivel'
        assert 'placar' in mesa_dict


class TestPlacar:
    """Testa modelo Placar"""
    
    def test_criar_placar(self, app_context, mesa):
        """Testa criação de placar"""
        placar = mesa.placar
        assert placar.id is not None
        assert placar.pontos_time1 == 0
        assert placar.pontos_time2 == 0
        assert placar.set_numero == 1
    
    def test_placar_inicial(self, app_context, mesa):
        """Testa estado inicial do placar"""
        placar = mesa.placar
        assert placar.pontos_time1 == 0
        assert placar.pontos_time2 == 0
        assert placar.sets_time1 == 0
        assert placar.sets_time2 == 0
        assert placar.servidor_time == 1
        assert placar.serves_no_set == 0
        assert placar.status == 'em_andamento'
    
    def test_placar_adicionar_pontos(self, app_context, mesa):
        """Testa adição de pontos"""
        placar = mesa.placar
        placar.pontos_time1 = 5
        placar.pontos_time2 = 3
        from models import db
        db.session.commit()
        
        placar_atualizado = Placar.query.get(placar.id)
        assert placar_atualizado.pontos_time1 == 5
        assert placar_atualizado.pontos_time2 == 3
    
    def test_placar_trocar_servidor(self, app_context, mesa):
        """Testa mudança de servidor"""
        placar = mesa.placar
        placar.servidor_time = 2
        from models import db
        db.session.commit()
        
        placar_atualizado = Placar.query.get(placar.id)
        assert placar_atualizado.servidor_time == 2
    
    def test_placar_novo_set(self, app_context, mesa):
        """Testa avanço para novo set"""
        placar = mesa.placar
        placar.set_numero = 2
        placar.sets_time1 = 1
        placar.pontos_time1 = 0
        placar.pontos_time2 = 0
        from models import db
        db.session.commit()
        
        placar_atualizado = Placar.query.get(placar.id)
        assert placar_atualizado.set_numero == 2
        assert placar_atualizado.sets_time1 == 1
    
    def test_placar_to_dict(self, app_context, mesa):
        """Testa conversão para dicionário"""
        placar_dict = mesa.placar.to_dict()
        assert placar_dict['pontos_time1'] == 0
        assert placar_dict['pontos_time2'] == 0
        assert placar_dict['set_numero'] == 1
        assert placar_dict['servidor_time'] == 1


class TestJogador:
    """Testa modelo Jogador"""
    
    def test_criar_jogador(self, app_context, mesa):
        """Testa criação de jogador"""
        jogador = Jogador(
            nome='Teste Jogador',
            mesa_id=mesa.id,
            time=1
        )
        from models import db
        db.session.add(jogador)
        db.session.commit()
        
        assert jogador.id is not None
        assert jogador.nome == 'Teste Jogador'
        assert jogador.time == 1
    
    def test_jogador_sets_vencidos(self, app_context, mesa):
        """Testa contador de sets vencidos"""
        jogador = Jogador(
            nome='Jogador',
            mesa_id=mesa.id,
            time=1
        )
        from models import db
        db.session.add(jogador)
        db.session.commit()
        
        assert jogador.sets_vencidos == 0
        
        jogador.sets_vencidos = 2
        db.session.commit()
        
        jogador_atualizado = Jogador.query.get(jogador.id)
        assert jogador_atualizado.sets_vencidos == 2
    
    def test_jogador_to_dict(self, app_context, mesa):
        """Testa conversão para dicionário"""
        jogador = Jogador(
            nome='Jogador',
            mesa_id=mesa.id,
            time=1
        )
        from models import db
        db.session.add(jogador)
        db.session.commit()
        
        jogador_dict = jogador.to_dict()
        assert jogador_dict['nome'] == 'Jogador'
        assert jogador_dict['time'] == 1
        assert jogador_dict['sets_vencidos'] == 0
