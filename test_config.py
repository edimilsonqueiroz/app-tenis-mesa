#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test configuration and database connection
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_config():
    """Test configuration loading"""
    print("\n" + "="*70)
    print("🔍 TESTE DE CONFIGURAÇÃO")
    print("="*70)
    
    from dotenv import load_dotenv
    load_dotenv()
    
    import config as cfg
    from app import app
    
    # Environment info
    print(f"\n📍 Ambiente: {cfg.ENVIRONMENT.upper()}")
    print(f"🔨 Tipo: {'PRODUÇÃO' if cfg.IS_PRODUCTION else 'DESENVOLVIMENTO'}")
    print(f"🐛 Debug: {app.debug}")
    print(f"🧪 Testing: {app.testing}")
    
    # Database info
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if 'postgresql' in db_uri:
        db_type = "PostgreSQL 🐘"
        # Ocultar senha
        masked_uri = db_uri.replace(
            db_uri.split('@')[0].split('://')[1],
            "****:****"
        )
        print(f"\n🗄️  Banco de Dados: {db_type}")
        print(f"   URI: {masked_uri}")
    elif 'sqlite' in db_uri:
        db_type = "SQLite 📄"
        db_path = db_uri.replace('sqlite:///', '')
        print(f"\n🗄️  Banco de Dados: {db_type}")
        print(f"   Path: {db_path}")
    
    # Secret Key
    secret_key = app.config.get('SECRET_KEY')
    if secret_key == 'dev-secret-key-only-for-development':
        print(f"\n🔑 SECRET_KEY: Usando fallback de desenvolvimento")
        print(f"   ⚠️  AVISO: Não use em produção!")
    else:
        key_mask = secret_key[:8] + "..." if secret_key else "NÃO CONFIGURADA"
        print(f"\n🔑 SECRET_KEY: {key_mask}")

def test_database_connection():
    """Test database connection"""
    print("\n" + "="*70)
    print("🔌 TESTE DE CONEXÃO COM BANCO DE DADOS")
    print("="*70 + "\n")
    
    try:
        from app import app, db
        
        with app.app_context():
            # Try simple query
            print("⏳ Conectando ao banco...")
            result = db.session.execute("SELECT 1")
            print("✅ Conexão bem-sucedida!")
            
            # Check tables
            print("\n📋 Verificando tabelas...")
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            
            if not tables:
                print("   ⚠️  Nenhuma tabela encontrada. Execute db.create_all() para criar.")
            else:
                print(f"   ✅ Encontradas {len(tables)} tabelas:")
                for table in tables:
                    columns = len(inspector.get_columns(table))
                    print(f"      - {table} ({columns} colunas)")
            
            return True
            
    except Exception as e:
        print(f"❌ Erro ao conectar: {type(e).__name__}: {e}")
        
        # Provide helpful hints
        print("\n💡 Dicas:")
        if 'postgresql' in str(e).lower():
            print("   - PostgreSQL não está acessível")
            print("   - Verifique se o servidor está rodando")
            print("   - Verifique credenciais em .env")
        elif 'password' in str(e).lower():
            print("   - Erro de autenticação")
            print("   - Verifique DB_PASSWORD em .env")
        
        return False

def test_environment_variables():
    """Test environment variables"""
    print("\n" + "="*70)
    print("🌍 TESTE DE VARIÁVEIS DE AMBIENTE")
    print("="*70 + "\n")
    
    import config as cfg
    
    # Check required vars in production
    if cfg.IS_PRODUCTION:
        print("🔴 MODO PRODUÇÃO - Verificando variáveis obrigatórias...\n")
        
        required = {
            'SECRET_KEY': os.environ.get('SECRET_KEY'),
            'DB_USER': os.environ.get('DB_USER'),
            'DB_PASSWORD': os.environ.get('DB_PASSWORD'),
            'DB_HOST': os.environ.get('DB_HOST'),
            'DB_NAME': os.environ.get('DB_NAME'),
        }
        
        all_ok = True
        for var, value in required.items():
            status = "✅" if value else "❌"
            print(f"{status} {var}: {'Configurada' if value else 'NÃO CONFIGURADA'}")
            if not value:
                all_ok = False
        
        if all_ok:
            print("\n✅ Todas as variáveis obrigatórias estão configuradas!")
        else:
            print("\n❌ Algumas variáveis obrigatórias não estão configuradas!")
            print("   Crie um arquivo .env com as variáveis necessárias")
    else:
        print("🟢 MODO DESENVOLVIMENTO\n")
        print("✅ SQLite será usado automaticamente")
        print("✅ SECRET_KEY com fallback de desenvolvimento")

def main():
    """Run all tests"""
    print("\n")
    print("╔" + "="*68 + "╗")
    print("║" + " "*15 + "TESTE DE CONFIGURAÇÃO DO PROJETO" + " "*21 + "║")
    print("╚" + "="*68 + "╝")
    
    test_environment_variables()
    test_config()
    db_ok = test_database_connection()
    
    # Summary
    print("\n" + "="*70)
    print("📊 RESUMO")
    print("="*70)
    
    if db_ok:
        print("✅ Configuração OK - Pronto para usar!")
    else:
        print("❌ Há problemas na configuração - Ver detalhes acima")
    
    print("\n")
    return 0 if db_ok else 1

if __name__ == '__main__':
    sys.exit(main())
