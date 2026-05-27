"""Testes para chaveamento por categoria em campeonatos."""
import json
from models import Campeonato, ResultadoPartida, JogadorInscrito, db


class TestChaveamentoCampeonato:
    def _finalizar_jogo_time1(self, client, mesa_id):
        for _ in range(2):
            for i in range(11):
                client.post(
                    f'/api/placar/mesa/{mesa_id}/adicionar-ponto',
                    json={'time': 1}
                )
                if i < 9:
                    client.post(
                        f'/api/placar/mesa/{mesa_id}/adicionar-ponto',
                        json={'time': 2}
                    )

    def test_cadastra_jogador_com_categoria(self, client, campeonato):
        response = client.post(
            f'/api/campeonatos/{campeonato.id}/jogadores-inscritos',
            json={
                'nome': 'Ana',
                'categoria': 'Sub-15'
            }
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['nome'] == 'Ana'
        assert data['categoria'] == 'Sub-15'

    def test_gera_chaveamento_agrupado_por_categoria(self, client, campeonato):
        jogadores = [
            {'nome': 'Ana', 'categoria': 'Sub-15'},
            {'nome': 'Bia', 'categoria': 'Sub-15'},
            {'nome': 'Caio', 'categoria': 'Sub-15'},
            {'nome': 'Duda', 'categoria': 'Adulto'},
            {'nome': 'Enzo', 'categoria': 'Adulto'}
        ]

        for jogador in jogadores:
            response = client.post(
                f'/api/campeonatos/{campeonato.id}/jogadores-inscritos',
                json=jogador
            )
            assert response.status_code == 201

        response = client.get(f'/api/campeonatos/{campeonato.id}/chaveamento')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['formato'] == 'eliminacao_simples'
        assert len(data['categorias']) == 2

        categoria_sub15 = next(item for item in data['categorias'] if item['categoria'] == 'Sub-15')
        categoria_adulto = next(item for item in data['categorias'] if item['categoria'] == 'Adulto')

        assert categoria_sub15['total_jogadores'] == 3
        assert categoria_sub15['tamanho_chave'] == 4
        assert categoria_sub15['rodadas'][0]['nome'] == 'Semifinais'
        assert any(partida['avanca_automaticamente'] for partida in categoria_sub15['rodadas'][0]['partidas'])

        assert categoria_adulto['total_jogadores'] == 2
        assert categoria_adulto['tamanho_chave'] == 2
        assert categoria_adulto['rodadas'][0]['nome'] == 'Final'

    def test_categoria_padrao_quando_nao_informada(self, client, campeonato):
        response = client.post(
            f'/api/campeonatos/{campeonato.id}/jogadores-inscritos',
            json={'nome': 'Jogador sem categoria'}
        )

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['categoria'] == 'Geral'

    def test_chaveamento_vivo_avanca_vencedor_para_proxima_partida(self, client, campeonato, mesa):
        mesa_final_response = client.post(
            '/api/mesas',
            json={'campeonato_id': campeonato.id, 'numero': 2}
        )
        assert mesa_final_response.status_code == 201
        mesa_final_id = json.loads(mesa_final_response.data)['id']

        jogadores = [
            {'nome': 'Ana', 'categoria': 'Sub-15'},
            {'nome': 'Bia', 'categoria': 'Sub-15'},
            {'nome': 'Caio', 'categoria': 'Sub-15'}
        ]
        for jogador in jogadores:
            response = client.post(
                f'/api/campeonatos/{campeonato.id}/jogadores-inscritos',
                json=jogador
            )
            assert response.status_code == 201

        response = client.post(f'/api/campeonatos/{campeonato.id}/chaveamento-vivo')
        assert response.status_code == 201
        data = json.loads(response.data)

        categoria = next(item for item in data['categorias'] if item['categoria'] == 'Sub-15')
        semifinal = next(partida for partida in categoria['rodadas'][0]['partidas'] if partida['status'] != 'bye')
        final = categoria['rodadas'][1]['partidas'][0]

        response = client.post(
            f'/api/campeonatos/{campeonato.id}/chaveamento/partidas/{final["id"]}/alocar-mesa',
            json={'mesa_id': mesa_final_id}
        )
        assert response.status_code == 200

        response = client.post(
            f'/api/campeonatos/{campeonato.id}/chaveamento/partidas/{semifinal["id"]}/alocar-mesa',
            json={'mesa_id': mesa.id}
        )
        assert response.status_code == 200

        self._finalizar_jogo_time1(client, mesa.id)

        response = client.get(f'/api/campeonatos/{campeonato.id}/chaveamento')
        assert response.status_code == 200
        data = json.loads(response.data)

        categoria = next(item for item in data['categorias'] if item['categoria'] == 'Sub-15')
        final_atualizada = categoria['rodadas'][1]['partidas'][0]
        nomes_final = {final_atualizada['jogador_1']['nome'], final_atualizada['jogador_2']['nome']}

        assert final_atualizada['status'] == 'em_andamento'
        assert nomes_final == {'Ana', 'Caio'}

        response = client.get(f'/api/mesas/{mesa_final_id}')
        assert response.status_code == 200
        mesa_final = json.loads(response.data)
        nomes_mesa_final = {jogador['nome'] for jogador in mesa_final['jogadores']}
        assert nomes_mesa_final == {'Ana', 'Caio'}

    def test_chaveamento_vivo_define_campeao_ao_finalizar_final(self, client, campeonato, mesa):
        for nome in ['Ana', 'Bia']:
            response = client.post(
                f'/api/campeonatos/{campeonato.id}/jogadores-inscritos',
                json={'nome': nome, 'categoria': 'Adulto'}
            )
            assert response.status_code == 201

        response = client.post(f'/api/campeonatos/{campeonato.id}/chaveamento-vivo')
        assert response.status_code == 201
        data = json.loads(response.data)

        categoria = next(item for item in data['categorias'] if item['categoria'] == 'Adulto')
        final = categoria['rodadas'][0]['partidas'][0]

        response = client.post(
            f'/api/campeonatos/{campeonato.id}/chaveamento/partidas/{final["id"]}/alocar-mesa',
            json={'mesa_id': mesa.id}
        )
        assert response.status_code == 200

        self._finalizar_jogo_time1(client, mesa.id)

        response = client.get(f'/api/campeonatos/{campeonato.id}/chaveamento')
        assert response.status_code == 200
        data = json.loads(response.data)
        categoria = next(item for item in data['categorias'] if item['categoria'] == 'Adulto')

        assert categoria['campeao']['nome'] == 'Ana'
        assert categoria['rodadas'][0]['partidas'][0]['status'] == 'finalizada'


class TestExclusaoCampeonato:
    def test_excluir_campeonato_remove_dados_do_ranking(self, client, app_context):
        campeonato_1 = Campeonato(nome='Camp Excluir 1', descricao='Remover tudo')
        campeonato_2 = Campeonato(nome='Camp Excluir 2', descricao='Manter dados')
        db.session.add_all([campeonato_1, campeonato_2])
        db.session.flush()

        db.session.add_all([
            JogadorInscrito(nome='Ana Ranking', campeonato_id=campeonato_1.id),
            JogadorInscrito(nome='Bia Ranking', campeonato_id=campeonato_2.id)
        ])

        db.session.add_all([
            ResultadoPartida(
                campeonato_id=campeonato_1.id,
                jogadores_time1='Ana Ranking',
                jogadores_time2='Vazio',
                pontos_time1=11,
                pontos_time2=0,
                sets_time1=2,
                sets_time2=0,
                vencedor_time=1
            ),
            ResultadoPartida(
                campeonato_id=campeonato_2.id,
                jogadores_time1='Bia Ranking',
                jogadores_time2='Vazio',
                pontos_time1=11,
                pontos_time2=0,
                sets_time1=2,
                sets_time2=0,
                vencedor_time=1
            )
        ])
        db.session.commit()

        response = client.delete(f'/api/campeonatos/{campeonato_1.id}')
        assert response.status_code == 200

        assert Campeonato.query.get(campeonato_1.id) is None
        assert ResultadoPartida.query.filter_by(campeonato_id=campeonato_1.id).count() == 0
        assert JogadorInscrito.query.filter_by(campeonato_id=campeonato_1.id).count() == 0
        assert ResultadoPartida.query.filter_by(campeonato_id=campeonato_2.id).count() == 1

        ranking_response = client.get('/api/ranking')
        assert ranking_response.status_code == 200
        ranking = json.loads(ranking_response.data)

        campeonatos_no_ranking = {
            campeonato['id']
            for jogador in ranking
            for campeonato in jogador.get('campeonatos', [])
        }

        assert campeonato_1.id not in campeonatos_no_ranking
        assert campeonato_2.id in campeonatos_no_ranking
