"""
Configuração compartilhada de fixtures para todos os testes
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app import app, db
from models import Campeonato, Mesa, Placar, Jogador


@pytest.fixture(scope='function')
def test_app():
    """Cria aplicação Flask em modo de teste com banco isolado por teste"""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture(scope='function')
def client(test_app):
    """Cliente de teste para fazer requisições HTTP"""
    return test_app.test_client()


@pytest.fixture(scope='function')
def app_context(test_app):
    """Contexto de aplicação para trabalhar com banco"""
    with test_app.app_context():
        yield test_app


@pytest.fixture(scope='function')
def campeonato(app_context):
    """Cria um campeonato de teste"""
    camp = Campeonato(
        nome='Teste',
        descricao='Campeonato de teste'
    )
    db.session.add(camp)
    db.session.commit()
    return camp


@pytest.fixture(scope='function')
def mesa(app_context, campeonato):
    """Cria uma mesa de teste"""
    mesa_obj = Mesa(
        numero=1,
        campeonato_id=campeonato.id,
        status='disponivel'
    )
    db.session.add(mesa_obj)
    db.session.commit()
    
    # Criar placar
    placar = Placar(mesa_id=mesa_obj.id)
    db.session.add(placar)
    db.session.commit()
    
    return mesa_obj


@pytest.fixture(scope='function')
def mesa_com_jogadores(app_context, mesa):
    """Cria mesa com 2 jogadores"""
    jogador1 = Jogador(
        nome='Jogador 1',
        mesa_id=mesa.id,
        time=1
    )
    jogador2 = Jogador(
        nome='Jogador 2',
        mesa_id=mesa.id,
        time=2
    )
    db.session.add_all([jogador1, jogador2])
    db.session.commit()
    
    # Mudar status para em_uso
    mesa.status = 'em_uso'
    db.session.commit()
    
    return mesa
