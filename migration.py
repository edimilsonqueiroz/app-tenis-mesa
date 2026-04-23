#!/usr/bin/env python
"""
Script de migração para adicionar colunas ao banco de dados.

Executa as seguintes migrações:
  1. servidor_inicial_jogo (placares) - para rastrear qual time começou sacando
  2. formato_jogo (placares) - para suportar múltiplos formatos de jogo
  3. sets_vencidos (jogadores) - para contabilizar sets vencidos por cada jogador
    4. lados_invertidos (placares) - para alternar exibição dos lados no placar
    5. auto_troca_lados_set (placares) - troca automática dos lados a cada novo set
    6. categoria (jogadores_inscritos) - para organizar o chaveamento por categoria

Execute este script uma vez para atualizar o banco de dados:
    python migration.py
"""

from app import app, db
from models import Placar
from sqlalchemy import inspect, text

def migrate():
    """Executa a migração"""
    with app.app_context():
        try:
            # Verifica quais colunas existem
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('placares')]
            
            migrations_aplicadas = []
            
            # Migração 1: servidor_inicial_jogo
            if 'servidor_inicial_jogo' not in columns:
                print("Adicionando coluna 'servidor_inicial_jogo' à tabela 'placares'...")
                with db.engine.begin() as connection:
                    connection.execute(text('''
                        ALTER TABLE placares 
                        ADD COLUMN servidor_inicial_jogo INTEGER DEFAULT 1
                    '''))
                migrations_aplicadas.append("[✓] Coluna 'servidor_inicial_jogo' adicionada")
            else:
                migrations_aplicadas.append("[✓] Coluna 'servidor_inicial_jogo' já existe")
            
            # Migração 2: formato_jogo
            if 'formato_jogo' not in columns:
                print("Adicionando coluna 'formato_jogo' à tabela 'placares'...")
                with db.engine.begin() as connection:
                    connection.execute(text('''
                        ALTER TABLE placares 
                        ADD COLUMN formato_jogo VARCHAR(20) DEFAULT 'melhor_de_3'
                    '''))
                migrations_aplicadas.append("[✓] Coluna 'formato_jogo' adicionada")
            else:
                migrations_aplicadas.append("[✓] Coluna 'formato_jogo' já existe")

            # Migração 2.1: lados_invertidos
            if 'lados_invertidos' not in columns:
                print("Adicionando coluna 'lados_invertidos' à tabela 'placares'...")
                with db.engine.begin() as connection:
                    connection.execute(text('''
                        ALTER TABLE placares
                        ADD COLUMN lados_invertidos BOOLEAN DEFAULT 0
                    '''))
                migrations_aplicadas.append("[✓] Coluna 'lados_invertidos' adicionada")
            else:
                migrations_aplicadas.append("[✓] Coluna 'lados_invertidos' já existe")

            # Migração 2.2: auto_troca_lados_set
            if 'auto_troca_lados_set' not in columns:
                print("Adicionando coluna 'auto_troca_lados_set' à tabela 'placares'...")
                with db.engine.begin() as connection:
                    connection.execute(text('''
                        ALTER TABLE placares
                        ADD COLUMN auto_troca_lados_set BOOLEAN DEFAULT 0
                    '''))
                migrations_aplicadas.append("[✓] Coluna 'auto_troca_lados_set' adicionada")
            else:
                migrations_aplicadas.append("[✓] Coluna 'auto_troca_lados_set' já existe")
            
            # Migração 3: sets_vencidos (na tabela jogadores)
            jogadores_columns = [col['name'] for col in inspector.get_columns('jogadores')]
            if 'sets_vencidos' not in jogadores_columns:
                print("Adicionando coluna 'sets_vencidos' à tabela 'jogadores'...")
                with db.engine.begin() as connection:
                    connection.execute(text('''
                        ALTER TABLE jogadores 
                        ADD COLUMN sets_vencidos INTEGER DEFAULT 0
                    '''))
                migrations_aplicadas.append("[✓] Coluna 'sets_vencidos' adicionada")
            else:
                migrations_aplicadas.append("[✓] Coluna 'sets_vencidos' já existe")
            
            # Migração 4: pontos_marcados (na tabela jogadores)
            if 'pontos_marcados' not in jogadores_columns:
                print("Adicionando coluna 'pontos_marcados' à tabela 'jogadores'...")
                with db.engine.begin() as connection:
                    connection.execute(text('''
                        ALTER TABLE jogadores 
                        ADD COLUMN pontos_marcados INTEGER DEFAULT 0
                    '''))
                migrations_aplicadas.append("[✓] Coluna 'pontos_marcados' adicionada")
            else:
                migrations_aplicadas.append("[✓] Coluna 'pontos_marcados' já existe")

            # Migração 5: categoria (na tabela jogadores_inscritos)
            inscritos_columns = [col['name'] for col in inspector.get_columns('jogadores_inscritos')]
            if 'categoria' not in inscritos_columns:
                print("Adicionando coluna 'categoria' à tabela 'jogadores_inscritos'...")
                with db.engine.begin() as connection:
                    connection.execute(text('''
                        ALTER TABLE jogadores_inscritos
                        ADD COLUMN categoria VARCHAR(50) DEFAULT 'Geral' NOT NULL
                    '''))
                migrations_aplicadas.append("[✓] Coluna 'categoria' adicionada")
            else:
                migrations_aplicadas.append("[✓] Coluna 'categoria' já existe")
            
            return migrations_aplicadas
        
        except Exception as e:
            print(f"✗ Erro durante migração: {e}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == '__main__':
    print("=" * 70)
    print("MIGRAÇÃO: Suporte a Contabilização de Sets por Jogador")
    print("=" * 70)
    
    migrações = migrate()
    
    print("\nMigrações aplicadas:")
    for msg in migrações:
        print(f"  {msg}")
    
    print("\nNovas funcionalidades:")
    print("  • Contabilização automática de sets vencidos por cada jogador")
    print("  • Suporte a múltiplos formatos de jogo (melhor de 3, 5 ou 7)")
    print("  • Rastreamento de servidor inicial para cálculos ITTF")
    print("  • Chaveamento simples agrupado por categoria dos inscritos")
    
    print("\nFormatos de jogo disponíveis:")
    print("  • melhor_de_3: Primeiro a vencer 2 sets (padrão)")
    print("  • melhor_de_5: Primeiro a vencer 3 sets")
    print("  • melhor_de_7: Primeiro a vencer 4 sets")
    
    print("=" * 70)
    print("Migração concluída! Aplicação pronta para usar.")
    print("=" * 70)
