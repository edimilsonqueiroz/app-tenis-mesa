let socket = io();

        socket.on('connect', function() {
            console.log('Conectado ao servidor');
            carregarCampeonatos();
        });

        socket.on('campeonato_criado', function(data) {
            carregarCampeonatos();
        });

        socket.on('campeonato_deletado', function(data) {
            carregarCampeonatos();
        });

        function carregarCampeonatos() {
            fetch('/api/campeonatos')
                .then(response => response.json())
                .then(campeonatos => {
                    const container = document.getElementById('campeonatos-list');
                    
                    if (!Array.isArray(campeonatos) || campeonatos.length === 0) {
                        container.innerHTML = `
                            <div class="empty">
                                <p>📭 Nenhum campeonato criado ainda</p>
                                <p>Clique em <strong><i class="fas fa-plus"></i> Novo Campeonato</strong> para começar</p>
                            </div>
                        `;
                        return;
                    }

                    container.innerHTML = campeonatos.map(camp => `
                        <div class="campeonato-card">
                            <h3>${camp.nome}</h3>
                            ${camp.descricao ? `<p class="descricao">${camp.descricao}</p>` : ''}
                            <div class="card-stats">
                                <span class="stat"><i class="fas fa-chess-board"></i> <strong>${camp.total_mesas}</strong> Mesa${camp.total_mesas !== 1 ? 's' : ''}</span>
                                <span class="stat"><i class="fas fa-circle-notch"></i> ${camp.status.charAt(0).toUpperCase() + camp.status.slice(1)}</span>
                            </div>
                            <div class="card-actions">
                                <button class="btn btn-sm btn-primary" onclick="abrirCampeonato(${camp.id})">
                                    ⚙️ Gerenciar
                                </button>
                                <button class="btn btn-sm btn-danger" onclick="deletarCampeonato(${camp.id})">
                                    <i class="fas fa-trash"></i> Deletar
                                </button>
                            </div>
                        </div>
                    `).join('');
                })
                .catch(error => {
                    console.error('Erro ao carregar campeonatos:', error);
                    document.getElementById('campeonatos-list').innerHTML = `
                        <div class="empty">
                            <p>📭 Nenhum campeonato criado ainda</p>
                            <p>Clique em <strong><i class="fas fa-plus"></i> Novo Campeonato</strong> para começar</p>
                        </div>
                    `;
                });
        }

        function abrirCriarCampeonato() {
            document.getElementById('modal-criar-campeonato').classList.remove('hide');
        }

        function fecharModal(modalId) {
            document.getElementById(modalId).classList.add('hide');
        }

        function criarCampeonato(event) {
            event.preventDefault();

            const nome = document.getElementById('nome-campeonato').value;
            const descricao = document.getElementById('descricao-campeonato').value;

            fetch('/api/campeonatos', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    nome: nome,
                    descricao: descricao
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.id) {
                    alert('✅ Campeonato criado com sucesso!');
                    fecharModal('modal-criar-campeonato');
                    document.getElementById('form-criar-campeonato').reset();
                    carregarCampeonatos();
                } else {
                    alert('Erro: ' + (data.erro || 'Desconhecido'));
                }
            })
            .catch(error => {
                console.error('Erro ao criar campeonato:', error);
                alert('Erro ao criar campeonato');
            });
        }

        function abrirCampeonato(campeonatoId) {
            window.location.href = `/campeonato/${campeonatoId}`;
        }

        function deletarCampeonato(campeonatoId) {
            if (!confirm('Tem certeza que deseja deletar este campeonato? Esta ação não pode ser desfeita.')) return;

            fetch(`/api/campeonatos/${campeonatoId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                alert('✅ Campeonato deletado com sucesso');
                carregarCampeonatos();
            })
            .catch(error => {
                console.error('Erro ao deletar campeonato:', error);
                alert('Erro ao deletar campeonato');
            });
        }

        // Fechar modal ao clicar fora dele
        window.onclick = function(event) {
            const modal = document.getElementById('modal-criar-campeonato');
            if (event.target === modal) {
                modal.classList.add('hide');
            }
        }
