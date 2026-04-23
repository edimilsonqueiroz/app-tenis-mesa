#!/usr/bin/env python
"""Script para popular o banco com dados de teste"""

from app import app, db
from models import Campeonato, JogadorInscrito

def seed():
    """Popula o banco com dados de teste"""
    with app.app_context():
        # Limpar dados existentes
        db.session.query(JogadorInscrito).delete()
        db.session.query(Campeonato).delete()
        db.session.commit()
        
        # Criar campeonato
        camp = Campeonato(
            nome='Torneio Teste',
            descricao='Torneio para testes',
            status='ativo'
        )
        db.session.add(camp)
        db.session.flush()
        
        # Criar jogadores inscritos
        jogadores = [
            JogadorInscrito(nome='EDIMILSON QUEIROZ', categoria='Geral', nivel='avançado', campeonato_id=camp.id),
            JogadorInscrito(nome='PAULO SILVA', categoria='Geral', nivel='intermediário', campeonato_id=camp.id),
            JogadorInscrito(nome='EDSON LOPES', categoria='Geral', nivel='iniciante', campeonato_id=camp.id),
            JogadorInscrito(nome='JOÃO SANTOS', categoria='Geral', nivel='avançado', campeonato_id=camp.id),
            JogadorInscrito(nome='MARIA OLIVEIRA', categoria='Feminino', nivel='intermediário', campeonato_id=camp.id),
        ]
        
        for j in jogadores:
            db.session.add(j)
        
        db.session.commit()
        
        print("✅ Banco de dados populado com dados de teste!")
        print(f"   - 1 campeonato criado: {camp.nome}")
        print(f"   - {len(jogadores)} jogadores inscritos")
        
        # Verificar ranking
        import requests
        try:
            resp = requests.get('http://localhost:5000/api/ranking')
            if resp.status_code == 200:
                ranking = resp.json()
                print(f"\n📊 Ranking atual: {len(ranking)} jogadores")
                for i, j in enumerate(ranking[:5], 1):
                    print(f"   {i}. {j['nome']} - {j['total_pontos']} pts, {j['total_sets']} sets")
        except Exception as e:
            print(f"⚠️ Não foi possível verificar o ranking (servidor não está rodando): {e}")

if __name__ == '__main__':
    seed()
