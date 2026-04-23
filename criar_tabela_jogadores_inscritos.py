#!/usr/bin/env python
"""
Script para criar a tabela de jogadores inscritos e adicionar as colunas necessárias.
Execute este script para aplicar as mudanças ao banco de dados.
"""

from app import app, db
from models import JogadorInscrito
from sqlalchemy import inspect, text

def migrate():
    """Executa a migração"""
    with app.app_context():
        try:
            print("🔄 Iniciando migração...")
            
            # Verifica se a tabela jogadores_inscritos existe
            inspector = inspect(db.engine)
            tabelas = inspector.get_table_names()
            
            if 'jogadores_inscritos' not in tabelas:
                print("✓ Criando tabela 'jogadores_inscritos'...")
                db.create_all()
                print("✓ Tabela 'jogadores_inscritos' criada com sucesso")
            else:
                print("✓ Tabela 'jogadores_inscritos' já existe")
            
            # Verifica se a coluna jogador_inscrito_id existe na tabela jogadores
            jogadores_columns = [col['name'] for col in inspector.get_columns('jogadores')]
            
            if 'jogador_inscrito_id' not in jogadores_columns:
                print("✓ Adicionando coluna 'jogador_inscrito_id' à tabela 'jogadores'...")
                with db.engine.begin() as connection:
                    connection.execute(text('''
                        ALTER TABLE jogadores 
                        ADD COLUMN jogador_inscrito_id INTEGER
                    '''))
                print("✓ Coluna 'jogador_inscrito_id' adicionada com sucesso")
            else:
                print("✓ Coluna 'jogador_inscrito_id' já existe")
            
            print("\n✅ Migração concluída com sucesso!")
            print("\nEndpoints disponíveis:")
            print("  GET    /api/campeonatos/<id>/jogadores-inscritos")
            print("  POST   /api/campeonatos/<id>/jogadores-inscritos")
            print("  PUT    /api/campeonatos/<id>/jogadores-inscritos/<jogador_id>")
            print("  DELETE /api/campeonatos/<id>/jogadores-inscritos/<jogador_id>")
            
        except Exception as e:
            print(f"❌ Erro durante a migração: {e}")
            return False
    
    return True

if __name__ == '__main__':
    sucesso = migrate()
    exit(0 if sucesso else 1)
