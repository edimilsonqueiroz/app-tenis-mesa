#!/usr/bin/env python
"""
Script para testar a API de ranking.
"""
from config import config
from models import db, Jogador, JogadorInscrito, Mesa, Campeonato, Placar
from flask import Flask
import json

# Criar app Flask
app = Flask(__name__)
app.config.from_object(config)
db.init_app(app)

# Importar rotas
from routes import register_blueprints
register_blueprints(app)

with app.app_context():
    print("\n=== Teste do Ranking ===\n")
    
    # Verificar dados no banco
    print(f"Total de campeonatos: {Campeonato.query.count()}")
    print(f"Total de jogadores inscritos: {JogadorInscrito.query.count()}")
    print(f"Total de jogadores em mesas: {Jogador.query.count()}")
    print(f"Total de mesas: {Mesa.query.count()}")
    
    # Testar a API
    try:
        with app.test_client() as client:
            response = client.get('/api/ranking')
            print(f"\nStatus Code: {response.status_code}")
            print(f"Content Type: {response.content_type}")
            
            if response.status_code == 200:
                data = response.get_json()
                print(f"Total de jogadores no ranking: {len(data)}")
                
                if data:
                    print("\nPrimeiro jogador:")
                    print(json.dumps(data[0], indent=2, ensure_ascii=False))
                else:
                    print("\n⚠️ Nenhum jogador no ranking!")
                    
                    # Debug: mostrar dados brutos
                    print("\n=== Debug: Verificando dados em detalhe ===")
                    
                    # Checando JogadorInscrito
                    jogadores_inscritos = JogadorInscrito.query.all()
                    if jogadores_inscritos:
                        print(f"\nJogadores inscritos encontrados ({len(jogadores_inscritos)}):")
                        for j in jogadores_inscritos[:3]:
                            print(f"  - {j.nome} (campeonato_id: {j.campeonato_id})")
                            
                            # Ver jogadores vinculados
                            jogadores = Jogador.query.filter_by(jogador_inscrito_id=j.id).all()
                            print(f"    Jogadores em mesas: {len(jogadores)}")
                            for jog in jogadores[:2]:
                                print(f"      - {jog.nome} (pontos: {jog.pontos_marcados}, sets: {jog.sets_vencidos})")
                    
                    # Checando Jogador sem vinculação
                    avulsos = Jogador.query.filter(Jogador.jogador_inscrito_id.is_(None)).all()
                    if avulsos:
                        print(f"\nJogadores avulsos (sem vinculação): {len(avulsos)}")
                        for j in avulsos[:3]:
                            print(f"  - {j.nome} (pontos: {j.pontos_marcados}, sets: {j.sets_vencidos})")
                    else:
                        print("\nNenhum jogador avulso encontrado")
            else:
                print(f"Erro: {response.data}")
    except Exception as e:
        print(f"Erro ao testar API: {e}")
        import traceback
        traceback.print_exc()
