const campeonatoId = window.APP_CONFIG ? window.APP_CONFIG.campeonatoId : null;
let socket = io();

socket.on('connect', function() {
    console.log('Conectado ao servidor de placar');
    socket.emit('inscrever_campeonato', { campeonato_id: campeonatoId });
    carregarMesas();
});

socket.on('placar_atualizado', function(data) {
    atualizarPlacarMesa(data.mesa_id, data.placar);
});

socket.on('mesa_criada', function() {
    carregarMesas();
});

socket.on('mesa_deletada', function() {
    carregarMesas();
});

function carregarMesas() {
    fetch(`/api/campeonatos/${campeonatoId}/mesas`)
        .then(response => response.json())
        .then(mesas => {
            const container = document.getElementById('placar-container');

            if (mesas.length === 0) {
                container.innerHTML = '<p class="empty">Nenhuma mesa cadastrada neste campeonato</p>';
                return;
            }

            container.innerHTML = mesas.map(mesa => `
                <div class="mesa-placar" data-mesa-id="${mesa.id}">
                    <div class="mesa-informacoes">
                        <div class="mesa-numero"><i class="fas fa-chess-board" style="color: #00c9a7; margin-right: 10px;"></i>Mesa ${mesa.numero}</div>

                        <div class="jogadores-section">
                            <div class="time-jogadores">
                                <div class="time-label"><i class="fas fa-users" style="margin-right: 6px;"></i>TIME 1</div>
                                ${mesa.jogadores.filter(j => j.time === 1).map(j =>
                                    `<div class="jogador-item">${j.nome}</div>`
                                ).join('') || '<div class="jogador-item">Sem jogadores</div>'}
                            </div>
                            <div class="time-jogadores" style="margin-top: 12px;">
                                <div class="time-label"><i class="fas fa-users" style="margin-right: 6px;"></i>TIME 2</div>
                                ${mesa.jogadores.filter(j => j.time === 2).map(j =>
                                    `<div class="jogador-item">${j.nome}</div>`
                                ).join('') || '<div class="jogador-item">Sem jogadores</div>'}
                            </div>
                        </div>
                    </div>

                    <div class="placar-display">
                        <div class="time-placar">
                            <div class="pontos" data-time="1">${mesa.placar?.pontos_time1 || 0}</div>
                        </div>
                        <div class="vs-text">VS</div>
                        <div class="time-placar">
                            <div class="pontos" data-time="2">${mesa.placar?.pontos_time2 || 0}</div>
                        </div>
                    </div>

                    <div style="flex-shrink: 0;">
                        <button class="controle-remoto-btn" onclick="abrirControle(${mesa.id})">
                            <i class="fas fa-mobile-screen-button"></i> Controle
                        </button>
                    </div>
                </div>
            `).join('');

            mesas.forEach(mesa => {
                socket.emit('inscrever_mesa', { mesa_id: mesa.id });
            });
        })
        .catch(error => {
            console.error('Erro ao carregar mesas:', error);
            document.getElementById('placar-container').innerHTML = '<p class="error">Erro ao carregar mesas</p>';
        });
}

function atualizarPlacarMesa(mesaId, placar) {
    const mesaEl = document.querySelector(`[data-mesa-id="${mesaId}"]`);
    if (mesaEl) {
        mesaEl.querySelector('[data-time="1"]').textContent = placar.pontos_time1;
        mesaEl.querySelector('[data-time="2"]').textContent = placar.pontos_time2;
    }
}

function abrirControle(mesaId) {
    window.open(`/controle/${mesaId}`, '_blank');
}

function voltarInicio() {
    window.location.href = '/';
}
