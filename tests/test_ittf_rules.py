"""
Testes para as regras ITTF
"""
import pytest
from ittf_rules import (
    validar_ponto_ittf,
    proximo_servidor,
    proximo_set,
    gerar_status_jogo
)


class TestValidarPontoITTF:
    """Testa validação de ponto segundo regras ITTF"""
    
    def test_ponto_simples(self):
        """Testa ponto simples sem fim de set"""
        resultado = validar_ponto_ittf(5, 3)
        assert resultado['set_terminado'] == False
        assert resultado['vencedor'] is None
    
    def test_fim_set_11_pontos_diferenca_2(self):
        """Testa fim de set com 11+ pontos e 2+ de diferença"""
        resultado = validar_ponto_ittf(11, 9)
        assert resultado['set_terminado'] == True
        assert resultado['vencedor'] == 1
    
    def test_sem_fim_set_11_pontos_sem_diferenca(self):
        """Testa que 11 pontos sem 2 de diferença não encerra"""
        resultado = validar_ponto_ittf(11, 10)
        assert resultado['set_terminado'] == False
    
    def test_fim_set_deuce_time1_vence(self):
        """Testa fim de set em deuce - time 1 vence"""
        resultado = validar_ponto_ittf(12, 10)
        assert resultado['set_terminado'] == True
        assert resultado['vencedor'] == 1
    
    def test_fim_set_deuce_time2_vence(self):
        """Testa fim de set em deuce - time 2 vence"""
        resultado = validar_ponto_ittf(13, 15)
        assert resultado['set_terminado'] == True
        assert resultado['vencedor'] == 2
    
    def test_sem_fim_set_menos_11_pontos(self):
        """Testa que menos de 11 pontos nunca encerra"""
        resultado = validar_ponto_ittf(10, 10)
        assert resultado['set_terminado'] == False


class TestProximoServidor:
    """Testa lógica de alternância de servidor"""
    
    def test_proximo_servidor_primeiro_saque(self):
        """Testa primeiro saque de um servidor"""
        resultado = proximo_servidor(1, 0)
        assert resultado['proximo_servidor'] == 1
    
    def test_proximo_servidor_alterna_apos_2_saques(self):
        """Testa alternância após 2 saques"""
        resultado = proximo_servidor(1, 1)
        assert resultado['proximo_servidor'] == 2
    
    def test_proximo_servidor_em_deuce(self):
        """Testa servidor em deuce (alterna a cada ponto)"""
        resultado = proximo_servidor(1, 0, 10, 10)
        assert resultado['em_deuce'] == True
        assert resultado['proximo_servidor'] == 2


class TestProximoSet:
    """Testa transição de sets"""
    
    def test_proximo_set_continua(self):
        """Testa que o jogo continua após primeiro set"""
        resultado = proximo_set(
            sets_time1=1,
            sets_time2=1,
            vencedor_set=1,
            formato_jogo='melhor_de_5'
        )
        assert resultado['jogo_finalizado'] == False
        assert resultado['novo_set'] is not None
    
    def test_jogo_finalizado_time1_vence_melhor_de_3(self):
        """Testa fim do jogo quando time 1 vence com 2-0"""
        resultado = proximo_set(
            sets_time1=1,
            sets_time2=0,
            vencedor_set=1,
            formato_jogo='melhor_de_3'
        )
        assert resultado['vencedor_jogo'] == 1
    
    def test_jogo_continua_melhor_de_5(self):
        """Testa que jogo continua em melhor de 5"""
        resultado = proximo_set(
            sets_time1=1,
            sets_time2=1,
            vencedor_set=1,
            formato_jogo='melhor_de_5'
        )
        assert resultado['jogo_finalizado'] == False
    
    def test_jogo_finalizado_time1_vence_melhor_de_5(self):
        """Testa fim do jogo quando time 1 vence com 3-1"""
        resultado = proximo_set(
            sets_time1=2,
            sets_time2=1,
            vencedor_set=1,
            formato_jogo='melhor_de_5'
        )
        assert resultado['vencedor_jogo'] == 1


class TestGerarStatusJogo:
    """Testa geração de status do jogo"""
    
    def test_status_jogo_inicializado(self, app_context, mesa):
        """Testa status inicial do jogo"""
        placar = mesa.placar
        status = gerar_status_jogo(placar)
        
        assert status['pontos']['time1'] == 0
        assert status['pontos']['time2'] == 0
        assert status['sets']['numero_atual'] == 1
        assert status['servidor']['time_atual'] == 1
