document.addEventListener('DOMContentLoaded', carregarRanking);

function carregarRanking() {
    fetch('/api/ranking')
        .then(async response => {
            const contentType = response.headers.get('content-type') || '';
            if (!response.ok || !contentType.includes('application/json')) {
                throw new Error('Resposta invalida da API de ranking');
            }
            return response.json();
        })
        .then(ranking => {
            const container = document.getElementById('ranking-container');

            if (!ranking || ranking.length === 0) {
                container.innerHTML = `
                    <div class="empty-ranking">
                        <i class="fas fa-trophy"></i>
                        <p>Nenhum jogador no ranking ainda</p>
                        <p style="font-size: 14px;">Os jogadores aparecerao aqui apos participarem de jogos nos campeonatos.</p>
                    </div>
                `;
                return;
            }

            let html = `
                <div class="ranking-table-wrapper">
                    <table class="ranking-table">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Jogador</th>
                                <th>Pontos</th>
                                <th>Sets</th>
                                <th>Jogos</th>
                                <th>Campeonatos</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            ranking.forEach((jogador, index) => {
                const posicao = index + 1;
                let medalhaClass = '';
                let posicaoHtml = '';

                if (posicao <= 3) {
                    medalhaClass = `medalha medalha-${posicao}`;
                    posicaoHtml = `<span class="${medalhaClass}">${posicao}</span>`;
                } else {
                    posicaoHtml = `<span class="posicao">${posicao}</span>`;
                }

                const campeonatosHtml = jogador.campeonatos.map(c =>
                    `<span class="tag-campeonato">${c.nome} (${c.pontos}pts)</span>`
                ).join('');

                html += `
                    <tr>
                        <td>${posicaoHtml}</td>
                        <td>
                            <div class="jogador-nome">${jogador.nome}</div>
                            <div class="jogador-campeonatos">
                                ${jogador.campeonatos.length} campeonato${jogador.campeonatos.length !== 1 ? 's' : ''}
                            </div>
                        </td>
                        <td><span class="badge-pontos">${jogador.total_pontos}</span></td>
                        <td><span class="badge-sets">${jogador.total_sets}</span></td>
                        <td><span class="badge-jogos">${jogador.total_jogos}</span></td>
                        <td>
                            <div class="campeonatos-tags">
                                ${campeonatosHtml}
                            </div>
                        </td>
                    </tr>
                `;
            });

            html += `
                        </tbody>
                    </table>
                </div>
            `;

            container.innerHTML = html;
        })
        .catch(error => {
            console.error('Erro ao carregar ranking:', error);
            document.getElementById('ranking-container').innerHTML = `
                <div class="empty-ranking">
                    <i class="fas fa-trophy"></i>
                    <p>Nenhum jogador no ranking ainda</p>
                    <p style="font-size: 14px;">Os jogadores aparecerao aqui apos participarem de jogos nos campeonatos.</p>
                </div>
            `;
        });
}
