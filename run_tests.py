#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para executar testes e gerar relatório
"""
import subprocess
import sys
import os


def run_tests(args=None):
    """Executa testes com pytest"""
    print("="*70)
    print("🧪 EXECUTANDO TESTES DO SISTEMA TÊNIS DE MESA")
    print("="*70)
    print()
    
    if args is None:
        args = sys.argv[1:]
    
    # Padrão: executar com verbosidade
    if not args:
        args = ['-v', '--tb=short']
    
    cmd = ['pytest'] + args
    
    try:
        result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
        return result.returncode
    except FileNotFoundError:
        print("❌ pytest não encontrado. Instale com: pip install pytest")
        return 1


def run_coverage():
    """Executa testes com relatório de cobertura"""
    print("="*70)
    print("📊 GERANDO RELATÓRIO DE COBERTURA")
    print("="*70)
    print()
    
    cmd = [
        'pytest',
        '--cov=.',
        '--cov-report=html',
        '--cov-report=term-missing',
        '-v'
    ]
    
    try:
        result = subprocess.run(cmd, cwd=os.path.dirname(__file__))
        if result.returncode == 0:
            print()
            print("✅ Relatório gerado em: htmlcov/index.html")
        return result.returncode
    except FileNotFoundError:
        print("❌ pytest-cov não encontrado. Instale com: pip install pytest-cov")
        return 1


def main():
    """Função principal"""
    if len(sys.argv) > 1:
        if sys.argv[1] == 'coverage':
            return run_coverage()
        elif sys.argv[1] == 'fast':
            # Testes rápidos (pula testes lentos)
            return run_tests(['-v', '-m', 'not slow'])
        elif sys.argv[1] == 'unit':
            # Apenas testes unitários
            return run_tests(['-v', '-m', 'unit'])
        elif sys.argv[1] == 'integration':
            # Apenas testes de integração
            return run_tests(['-v', '-m', 'integration'])
        else:
            # Passar argumentos diretamente para pytest
            return run_tests(sys.argv[1:])
    else:
        # Executar todos os testes
        return run_tests()


if __name__ == '__main__':
    sys.exit(main())
