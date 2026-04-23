const campeonatoId = window.APP_CONFIG ? window.APP_CONFIG.campeonatoId : null;
        const modoPagina = window.APP_CONFIG ? window.APP_CONFIG.modoPagina : "mesas";
        const paginaMesas = modoPagina === 'mesas';
        const paginaJogadores = modoPagina === 'jogadores';
        const paginaChaveamento = modoPagina === 'chaveamento';
        let socket = io();
        let novosJogadores = {}; // Rastrear novos jogadores por mesa
        let jogadoresDisponiveisParaMesas = [];
        let buscaDigitadaPorMesa = {};
        let todasAsMesas = []; // Armazenar dados de todas as mesas

        socket.on('connect', function() {
            console.log('Conectado ao servidor');
            socket.emit('inscrever_campeonato', { campeonato_id: campeonatoId });
            carregarCampeonato();
        });

        socket.on('mesa_criada', function(data) {
            if (paginaMesas || paginaChaveamento) carregarMesas();
        });

        socket.on('mesa_deletada', function(data) {
            if (paginaMesas || paginaChaveamento) carregarMesas();
        });

        socket.on('placar_atualizado', function(data) {
            if (paginaMesas || paginaChaveamento) carregarMesas();
            if (paginaChaveamento) carregarTorneio();
        });

        socket.on('jogadores_atualizados', function(data) {
            console.log('👥 Jogadores atualizados - recarregando mesas');
            if (paginaMesas || paginaChaveamento) carregarMesas();
            if (paginaJogadores) carregarJogadoresInscritos();
            if (paginaChaveamento) carregarTorneio();
        });

        socket.on('mesa_atualizada', function(data) {
            console.log('🔄 Mesa atualizada - recarregando mesas');
            if (paginaMesas || paginaChaveamento) carregarMesas();
            if (paginaChaveamento) carregarTorneio();
        });

        socket.on('chaveamento_atualizado', function(data) {
            console.log('🏆 Chaveamento atualizado');
            if (paginaMesas || paginaChaveamento) carregarMesas();
            if (paginaChaveamento) carregarTorneio();
        });

        socket.on('controle_conectado', function(data) {
            console.log('✅ Controle remoto conectado para Mesa', data.mesa_id);
            // Fechar modal se estiver aberta para esta mesa
            const modal = document.getElementById('modalControle');
            if (modal) {
                console.log('Modal encontrada, verificando se tem classe show...', modal.classList.contains('show'));
                if (modal.classList.contains('show')) {
                    console.log('📱 QR code lido com sucesso! Fechando modal...');
                    fecharModalControle();
                } else {
                    console.log('⚠️ Modal não tem classe show, pode não estar visível');
                }
            } else {
                console.log('❌ Modal não encontrada');
            }
        });

        function carregarCampeonato() {
            fetch(`/api/campeonatos/${campeonatoId}`)
                .then(response => response.json())
                .then(campeonato => {
                    document.getElementById('nome-campeonato').textContent = campeonato.nome;
                    if (paginaMesas || paginaChaveamento) carregarMesas();
                    if (paginaJogadores) carregarJogadoresInscritos();
                    if (paginaChaveamento) carregarTorneio();
                })
                .catch(error => console.error('Erro ao carregar campeonato:', error));
        }

        function escapeHtml(valor) {
            return String(valor ?? '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function carregarMesas() {
            console.log(`📡 Carregando mesas para campeonato ${campeonatoId}...`);
            fetch(`/api/campeonatos/${campeonatoId}/mesas`)
                .then(response => {
                    console.log('📥 Resposta recebida:', response.status);
                    if (!response.ok) {
                        throw new Error(`Erro HTTP: ${response.status}`);
                    }
                    return response.json();
                })
                .then(mesasData => {
                    console.log('✅ Mesas carregadas:', mesasData);
                    todasAsMesas = mesasData;
                    const container = document.getElementById('mesas-container');
                    if (!container) {
                        return;
                    }
                    
                    if (mesasData.length === 0) {
                        container.innerHTML = '<p class="empty-message">Nenhuma mesa cadastrada. Crie uma nova mesa para começar!</p>';
                        return;
                    }

                    container.innerHTML = mesasData.map(mesa => `
                        <div class="mesa-card" data-mesa-id="${mesa.id}">
                            <div class="mesa-header">
                                <div class="mesa-numero">Mesa ${mesa.numero}</div>
                                <div class="mesa-status ${mesa.status === 'disponivel' ? '' : mesa.status === 'pausada' ? 'pausada' : 'indisponivel'}">${mesa.status === 'pausada' ? 'em pausa' : mesa.status}</div>
                            </div>

                            <div>
                                <strong>Placar:</strong>
                                ${mesa.placar ? `
                                    <div style="font-size: 24px; text-align: center; margin: 10px 0;">
                                        ${mesa.placar.pontos_time1} <strong>×</strong> ${mesa.placar.pontos_time2}
                                    </div>
                                ` : '<div style="text-align: center; color: #999;">Sem placar</div>'}
                            </div>

                            <div class="jogadores-list">
                                <strong>Jogadores:</strong>
                                ${mesa.jogadores.length > 0 ? mesa.jogadores.map(jogador => `
                                    <div class="jogador-item">
                                        <span><span class="jogador-time">Time ${jogador.time}:</span> ${jogador.nome}</span>
                                        <button class="btn-remover-jogador" onclick="removerJogador(${jogador.id})">Remover</button>
                                    </div>
                                `).join('') : '<div style="text-align: center; color: #999; padding: 10px;">Sem jogadores</div>'}
                            </div>

                            <div class="adicionar-jogador">
                                <select id="jogador-${mesa.id}" title="Digite no select para buscar por nome" onkeydown="filtrarJogadoresNoSelect(${mesa.id}, event)" onblur="limparBuscaJogadoresNoSelect(${mesa.id})">
                                    <option value="">-- Selecione um jogador --</option>
                                </select>
                                <select id="time-${mesa.id}">
                                    <option value="1">Time 1</option>
                                    <option value="2">Time 2</option>
                                </select>
                                <button onclick="adicionarJogador(${mesa.id})">+</button>
                            </div>

                            <div class="mesa-acoes">
                                <button class="btn-placar" onclick="abrirPlacarMesa(${mesa.id})"><i class="fas fa-eye"></i> Ver Placar</button>
                                <button class="btn-placar" onclick="abrirControle(${mesa.id})"><i class="fas fa-mobile-screen-button"></i> Controle</button>
                                <button class="btn-placar" onclick="abrirQRPrint(${mesa.id}, ${mesa.numero})" style="background: #9c27b0;"><i class="fas fa-qrcode"></i> QR</button>
                                <button class="btn-deletar-mesa" onclick="deletarMesa(${mesa.id})"><i class="fas fa-trash"></i> Deletar</button>
                            </div>
                        </div>
                    `).join('');
                    
                    // Carregar jogadores inscritos para cada select
                    carregarJogadoresParaSelects();
                })
                .catch(error => {
                    console.error('❌ Erro ao carregar mesas:', error);
                    const container = document.getElementById('mesas-container');
                    if (!container) {
                        return;
                    }
                    container.innerHTML = `<p style="color: red; padding: 20px;">Erro ao carregar mesas: ${error.message}</p>`;
                });
        }

        function carregarJogadoresParaSelects() {
            console.log(`📡 Carregando jogadores para preencher selects...`);
            fetch(`/api/campeonatos/${campeonatoId}/jogadores-inscritos`)
                .then(response => response.json())
                .then(jogadores => {
                    console.log('✅ Jogadores carregados para selects:', jogadores);
                    
                    // Coletar IDs de jogadores inscritos que já estão em alguma mesa
                    const idsOcupados = new Set();
                    todasAsMesas.forEach(mesa => {
                        mesa.jogadores.forEach(j => {
                            if (j.jogador_inscrito_id) {
                                idsOcupados.add(j.jogador_inscrito_id);
                            }
                        });
                    });

                    jogadoresDisponiveisParaMesas = jogadores.filter(j => !idsOcupados.has(j.id));
                    
                    // Encontrar todos os mesas e preencher seus selects
                    const mesaCards = document.querySelectorAll('.mesa-card');
                    mesaCards.forEach(mesaCard => {
                        const mesaId = mesaCard.getAttribute('data-mesa-id');
                        preencherSelectJogadores(mesaId, jogadoresDisponiveisParaMesas, '');
                    });
                })
                .catch(error => console.error('❌ Erro ao carregar jogadores para selects:', error));
        }

        function preencherSelectJogadores(mesaId, jogadores, filtro) {
            const selectElement = document.getElementById(`jogador-${mesaId}`);
            if (!selectElement) return;

            const valorSelecionadoAtual = selectElement.value;
            const termoBusca = (filtro || '').trim().toLowerCase();
            const jogadoresFiltrados = termoBusca
                ? jogadores.filter(jogador => jogador.nome.toLowerCase().includes(termoBusca))
                : jogadores;

            selectElement.innerHTML = '<option value="">-- Selecione um jogador --</option>';

            jogadoresFiltrados.forEach(jogador => {
                const option = document.createElement('option');
                option.value = jogador.id;
                option.textContent = `${jogador.nome} (${jogador.categoria || 'Geral'})`;
                selectElement.appendChild(option);
            });

            if (valorSelecionadoAtual && jogadoresFiltrados.some(j => String(j.id) === valorSelecionadoAtual)) {
                selectElement.value = valorSelecionadoAtual;
            } else if (termoBusca && jogadoresFiltrados.length > 0) {
                selectElement.value = String(jogadoresFiltrados[0].id);
            }

            if (jogadoresFiltrados.length === 0) {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'Nenhum jogador encontrado';
                option.disabled = true;
                selectElement.appendChild(option);
            }
        }

        function filtrarJogadoresNoSelect(mesaId, event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                adicionarJogador(mesaId);
                return;
            }

            if (event.ctrlKey || event.metaKey || event.altKey) return;

            const teclasIgnoradas = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'Tab', 'Shift', 'Control', 'Alt', 'Home', 'End', 'PageUp', 'PageDown'];
            if (teclasIgnoradas.includes(event.key)) return;

            const buscaAtual = buscaDigitadaPorMesa[mesaId] || '';
            let novaBusca = buscaAtual;

            if (event.key === 'Backspace') {
                novaBusca = buscaAtual.slice(0, -1);
                event.preventDefault();
            } else if (event.key === 'Escape') {
                novaBusca = '';
                event.preventDefault();
            } else if (event.key.length === 1) {
                novaBusca = `${buscaAtual}${event.key}`;
                event.preventDefault();
            } else {
                return;
            }

            buscaDigitadaPorMesa[mesaId] = novaBusca;
            preencherSelectJogadores(mesaId, jogadoresDisponiveisParaMesas, novaBusca);
        }

        function limparBuscaJogadoresNoSelect(mesaId) {
            buscaDigitadaPorMesa[mesaId] = '';
            preencherSelectJogadores(mesaId, jogadoresDisponiveisParaMesas, '');
        }

        function carregarJogadoresInscritos() {
            console.log(`📡 Carregando jogadores inscritos para campeonato ${campeonatoId}...`);
            fetch(`/api/campeonatos/${campeonatoId}/jogadores-inscritos`)
                .then(response => {
                    console.log('📥 Resposta de jogadores recebida:', response.status);
                    if (!response.ok) {
                        throw new Error(`Erro HTTP: ${response.status}`);
                    }
                    return response.json();
                })
                .then(jogadores => {
                    console.log('✅ Jogadores carregados:', jogadores);
                    const container = document.getElementById('jogadores-container');
                    const labelsNivel = {
                        iniciante: 'Iniciante',
                        intermediario: 'Intermediário',
                        avancado: 'Avançado'
                    };
                    
                    if (jogadores.length === 0) {
                        container.innerHTML = '<p class="loading">Nenhum jogador inscrito ainda.</p>';
                        carregarChaveamento();
                        return;
                    }

                    container.innerHTML = jogadores.map(jogador => `
                        <div class="jogador-item">
                            <span class="jogador-nome">
                                ${escapeHtml(jogador.nome)}
                                <span class="jogador-categoria">${escapeHtml(jogador.categoria || 'Geral')}</span>
                                <span class="jogador-categoria" style="background:#fef3c7;color:#92400e;">${escapeHtml(labelsNivel[jogador.nivel] || 'Iniciante')}</span>
                            </span>
                            <button class="jogador-remove" onclick="removerJogadorInscrito(${jogador.id})">
                                <i class="fas fa-trash"></i> Remover
                            </button>
                        </div>
                    `).join('');

                    carregarChaveamento();
                })
                .catch(error => {
                    console.error('❌ Erro ao carregar jogadores inscritos:', error);
                    const container = document.getElementById('jogadores-container');
                    container.innerHTML = `<p style="color: red; padding: 20px;">Erro ao carregar jogadores: ${error.message}</p>`;
                });
        }

        function renderizarPartidaJogador(jogador) {
            if (!jogador) {
                return '<div class="partida-jogador"><strong>A definir</strong><span>aguardando confronto</span></div>';
            }

            return `
                <div class="partida-jogador">
                    <strong>${escapeHtml(jogador.nome)}</strong>
                    <span>${escapeHtml(jogador.categoria || 'Geral')}</span>
                </div>
            `;
        }

        function obterLabelStatusPartida(status) {
            const labels = {
                pendente: 'Aguardando',
                pronta: 'Pronta',
                em_andamento: 'Em andamento',
                finalizada: 'Finalizada',
                bye: 'Bye',
                vazio: 'Vazio'
            };
            return labels[status] || status;
        }

        function renderizarAcoesPartida(partida) {
            if (!partida.id || partida.status === 'bye' || partida.status === 'vazio') {
                return '';
            }

            if (partida.status === 'finalizada') {
                if (!partida.mesa) return '';
                return `
                    <div class="partida-acoes">
                        <button class="btn-liberar-mesa" onclick="liberarMesaPartida(${partida.id})"><i class="fas fa-forward"></i> Liberar Mesa / Próxima Partida</button>
                    </div>
                `;
            }

            const opcoesMesas = todasAsMesas.length > 0
                ? todasAsMesas.map(mesa => `<option value="${mesa.id}" ${partida.mesa && partida.mesa.id === mesa.id ? 'selected' : ''}>Mesa ${mesa.numero}</option>`).join('')
                : '';

            if (!opcoesMesas) {
                return '<div class="partida-acoes"><span class="chaveamento-info">Crie uma mesa para alocar esta partida.</span></div>';
            }

            return `
                <div class="partida-acoes">
                    <select id="mesa-partida-${partida.id}">
                        ${opcoesMesas}
                    </select>
                    <button onclick="alocarPartidaNaMesa(${partida.id})">Alocar na Mesa</button>
                </div>
            `;
        }

        function renderizarPartida(partida) {
            return `
                <div class="partida-card ${escapeHtml(partida.status || 'pendente')}">
                    <div class="partida-header">
                        <span>Partida ${partida.numero}</span>
                        <span class="partida-status ${escapeHtml(partida.status || 'pendente')}">${escapeHtml(obterLabelStatusPartida(partida.status || 'pendente'))}</span>
                    </div>
                    ${renderizarPartidaJogador(partida.jogador_1)}
                    ${renderizarPartidaJogador(partida.jogador_2)}
                    ${partida.vencedor ? `<div class="partida-vencedor"><strong>Vencedor:</strong> ${escapeHtml(partida.vencedor.nome)}</div>` : ''}
                    ${partida.mesa ? `<div class="partida-mesa"><strong>Mesa:</strong> ${escapeHtml(String(partida.mesa.numero))}</div>` : ''}
                    ${partida.placar ? renderizarPlacarPartida(partida) : ''}
                    ${partida.avanca_automaticamente ? '<div class="partida-bye">Avanço automático por bye</div>' : ''}
                    ${renderizarAcoesPartida(partida)}
                </div>
            `;
        }

        function renderizarPlacarPartida(partida) {
            const p = partida.placar;
            if (!p) return '';

            const sets1 = p.sets_time1 ?? 0;
            const sets2 = p.sets_time2 ?? 0;
            const finalizado = partida.status === 'finalizada';
            const badgeClass = finalizado ? 'finalizado' : 'ao_vivo';

            let pontosLabel = '';
            if (!finalizado && (p.pontos_time1 !== undefined || p.pontos_time2 !== undefined)) {
                pontosLabel = `<span class="placar-pontos">(${p.pontos_time1 ?? 0} – ${p.pontos_time2 ?? 0} pts no set)</span>`;
            }

            const labelSets = finalizado ? 'Sets finais' : 'Sets ao vivo';
            return `<div class="partida-placar">
                <div style="font-size:11px;color:#64748b;margin-bottom:3px;font-weight:600;text-transform:uppercase;">${labelSets}</div>
                <span class="placar-badge ${badgeClass}">${sets1} × ${sets2}${pontosLabel}</span>
            </div>`;
        }

        function gerarChaveamentoVivo(force = false) {
            fetch(`/api/campeonatos/${campeonatoId}/chaveamento-vivo`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ force })
            })
            .then(response => response.json().then(data => ({ status: response.status, ok: response.ok, data })))
            .then(({ status, ok, data }) => {
                if (status === 409 && data.requer_confirmacao) {
                    const confirmado = confirm('Existem partidas em andamento ou finalizadas.\nDeseja realmente regenerar o chaveamento? Todos os resultados serão perdidos.');
                    if (confirmado) gerarChaveamentoVivo(true);
                    return;
                }
                if (!ok) throw new Error(data.erro || 'Erro ao gerar chaveamento vivo');
                carregarMesas();
                carregarTorneio();
            })
            .catch(error => { console.error(error); alert(error.message); });
        }

        function liberarMesaPartida(partidaId) {
            fetch(`/api/campeonatos/${campeonatoId}/chaveamento/partidas/${partidaId}/liberar-mesa`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json().then(data => ({ ok: response.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error(data.erro || 'Erro ao liberar mesa');
                carregarMesas(); carregarTorneio();
            })
            .catch(error => { console.error(error); alert(error.message); });
        }

        function alocarPartidaNaMesa(partidaId) {
            const select = document.getElementById(`mesa-partida-${partidaId}`);
            if (!select || !select.value) { alert('Selecione uma mesa para a partida'); return; }

            fetch(`/api/campeonatos/${campeonatoId}/chaveamento/partidas/${partidaId}/alocar-mesa`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mesa_id: parseInt(select.value) })
            })
            .then(response => response.json().then(data => ({ ok: response.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error(data.erro || 'Erro ao alocar partida');
                carregarMesas(); carregarTorneio();
            })
            .catch(error => { console.error(error); alert(error.message); });
        }

        // ---------- FASE DE GRUPOS ----------

        function gerarFaseGrupos() {
            const n = parseInt(prompt('Jogadores por grupo (padrão: 4):', '4') || '4');
            if (isNaN(n) || n < 2) { alert('Número inválido.'); return; }

            fetch(`/api/campeonatos/${campeonatoId}/fase-grupos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ jogadores_por_grupo: n })
            })
            .then(response => response.json().then(data => ({ ok: response.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error(data.erro || 'Erro ao gerar fase de grupos');
                carregarMesas(); carregarTorneio();
            })
            .catch(error => { console.error(error); alert(error.message); });
        }

        function avancarParaMataMata() {
            const confirmado = confirm('Avançar para o mata-mata? Os classificados de cada grupo serão gerados.');
            if (!confirmado) return;

            fetch(`/api/campeonatos/${campeonatoId}/avancar-mata-mata`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json().then(data => ({ ok: response.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error(data.erro || 'Erro ao avançar para mata-mata');
                carregarMesas(); carregarTorneio();
            })
            .catch(error => { console.error(error); alert(error.message); });
        }

        function alocarPartidaGrupoNaMesa(partidaId) {
            const select = document.getElementById(`mesa-partida-grupo-${partidaId}`);
            if (!select || !select.value) { alert('Selecione uma mesa para a partida'); return; }

            fetch(`/api/campeonatos/${campeonatoId}/grupos/partidas/${partidaId}/alocar-mesa`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ mesa_id: parseInt(select.value) })
            })
            .then(response => response.json().then(data => ({ ok: response.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error(data.erro || 'Erro ao alocar partida de grupo');
                carregarMesas(); carregarTorneio();
            })
            .catch(error => { console.error(error); alert(error.message); });
        }

        function liberarMesaPartidaGrupo(partidaId) {
            fetch(`/api/campeonatos/${campeonatoId}/grupos/partidas/${partidaId}/liberar-mesa`, {
                method: 'POST', headers: { 'Content-Type': 'application/json' }
            })
            .then(response => response.json().then(data => ({ ok: response.ok, data })))
            .then(({ ok, data }) => {
                if (!ok) throw new Error(data.erro || 'Erro ao liberar mesa');
                carregarMesas(); carregarTorneio();
            })
            .catch(error => { console.error(error); alert(error.message); });
        }

        // ---------- RENDERIZAÇÃO DE GRUPOS ----------

        function renderizarGrupo(grupo, categoria) {
            const letras = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
            const nomeGrupo = `Grupo ${letras[(grupo.numero - 1) % 26]}`;
            const statusLabels = { pendente: 'Pendente', em_andamento: 'Em andamento', finalizado: 'Finalizado' };
            const statusClasses = { pendente: 'pendente', em_andamento: 'em_andamento', finalizado: 'finalizada' };

            const classificacaoHtml = `
                <div class="classificacao-card">
                    <div class="classificacao-head">
                        <span><i class="fas fa-table-list"></i> Classificação</span>
                        <span>${grupo.classificacao.length} atleta(s)</span>
                    </div>
                    <div class="classificacao-table-wrap">
                        <table class="tabela-classificacao">
                            <thead><tr><th>Pos</th><th>Jogador</th><th>V</th><th>D</th><th>S+</th><th>S-</th><th>Pts</th></tr></thead>
                            <tbody>
                                ${grupo.classificacao.map(c => `
                                    <tr class="${c.avancou ? 'classificado' : ''}">
                                        <td>${c.posicao ?? '-'}</td>
                                        <td>${escapeHtml(c.jogador ? c.jogador.nome : '?')}${c.avancou ? ' <span style="font-size:10px;color:#166534;">✓</span>' : ''}</td>
                                        <td>${c.partidas_vencidas}</td>
                                        <td>${c.partidas_perdidas}</td>
                                        <td>${c.sets_vencidos}</td>
                                        <td>${c.sets_perdidos}</td>
                                        <td><strong>${c.pontos}</strong></td>
                                    </tr>`).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>`;

            const partidasHtml = grupo.partidas.length === 0 ? '' : `
                <div class="partidas-grupo-lista">
                    ${grupo.partidas.map(p => renderizarPartidaGrupo(p)).join('')}
                </div>`;

            return `
                <div class="grupo-card">
                    <div class="grupo-header">
                        <div>
                            <span class="grupo-titulo">${escapeHtml(nomeGrupo)} — ${escapeHtml(categoria)}</span>
                            <div class="grupo-subinfo">${grupo.partidas.length} partidas programadas</div>
                        </div>
                        <span class="partida-status ${statusClasses[grupo.status] || 'pendente'}">${statusLabels[grupo.status] || grupo.status}</span>
                    </div>
                    ${classificacaoHtml}
                    ${partidasHtml}
                </div>`;
        }

        function renderizarPartidaGrupo(partida) {
            const statusLabels = { pronta: 'Pronta', em_andamento: 'Em andamento', finalizada: 'Finalizada' };
            const finalizada = partida.status === 'finalizada';

            let acoesHtml = '';
            if (finalizada && partida.mesa) {
                acoesHtml = `<div class="partida-acoes"><button class="btn-liberar-mesa" onclick="liberarMesaPartidaGrupo(${partida.id})"><i class="fas fa-forward"></i> Liberar Mesa</button></div>`;
            } else if (!finalizada) {
                const opcoes = todasAsMesas.map(m =>
                    `<option value="${m.id}" ${partida.mesa && partida.mesa.id === m.id ? 'selected' : ''}>Mesa ${m.numero}</option>`
                ).join('');
                if (opcoes) {
                    acoesHtml = `<div class="partida-acoes">
                        <select id="mesa-partida-grupo-${partida.id}">${opcoes}</select>
                        <button onclick="alocarPartidaGrupoNaMesa(${partida.id})">Alocar</button>
                    </div>`;
                }
            }

            return `
                <div class="partida-card partida-grupo-card ${escapeHtml(partida.status || 'pronta')}">
                    <div class="partida-header">
                        <span>R${partida.rodada_grupo} · P${partida.posicao}</span>
                        <span class="partida-status ${escapeHtml(partida.status || 'pronta')}">${statusLabels[partida.status] || partida.status}</span>
                    </div>
                    ${renderizarPartidaJogador(partida.jogador_1)}
                    ${renderizarPartidaJogador(partida.jogador_2)}
                    ${partida.vencedor ? `<div class="partida-vencedor"><strong>Vencedor:</strong> ${escapeHtml(partida.vencedor.nome)}</div>` : ''}
                    ${partida.mesa ? `<div class="partida-mesa"><strong>Mesa:</strong> ${escapeHtml(String(partida.mesa.numero))}</div>` : ''}
                    ${partida.placar ? renderizarPlacarPartida(partida) : ''}
                    ${acoesHtml}
                </div>`;
        }

        // ---------- CARREGAMENTO PRINCIPAL ----------

        function carregarTorneio() {
            fetch(`/api/campeonatos/${campeonatoId}/torneio`)
                .then(response => {
                    if (!response.ok) throw new Error(`Erro HTTP: ${response.status}`);
                    return response.json();
                })
                .then(torneio => {
                    const faseLabels = {
                        sem_dados: 'Sem dados — cadastre jogadores e gere os grupos',
                        grupos: 'Fase de grupos em andamento',
                        aguardando_avanco: 'Grupos finalizados — pronto para avançar ao mata-mata',
                        mata_mata: 'Mata-mata em andamento',
                        concluido: 'Torneio concluído'
                    };
                    document.getElementById('torneio-fase-label').textContent = faseLabels[torneio.fase_atual] || torneio.fase_atual;

                    const btnAvancar = document.getElementById('btn-avancar-mata-mata');
                    btnAvancar.style.display = torneio.fase_atual === 'aguardando_avanco' ? '' : 'none';

                    // Grupos
                    const gruposSection = document.getElementById('grupos-section');
                    const gruposContainer = document.getElementById('grupos-container');
                    if (torneio.tem_grupos) {
                        gruposSection.style.display = '';
                        gruposContainer.innerHTML = torneio.categorias.map(cat =>
                            cat.grupos.map(g => renderizarGrupo(g, cat.categoria)).join('')
                        ).join('');
                    } else {
                        gruposSection.style.display = 'none';
                    }

                    // Mata-mata
                    const mataMataSection = document.getElementById('mata-mata-section');
                    const kkContainer = document.getElementById('chaveamento-container');
                    if (torneio.tem_mata_mata) {
                        mataMataSection.style.display = '';
                        if (torneio.tem_grupos) {
                            mataMataSection.querySelector('.subsection-title') || mataMataSection.insertAdjacentHTML('afterbegin', '<div class="subsection-title">Mata-Mata</div>');
                        }
                        const categoriasKo = torneio.categorias.filter(c => c.mata_mata && c.mata_mata.rodadas && c.mata_mata.rodadas.length > 0);
                        kkContainer.innerHTML = `<div class="chaveamento-grid">${categoriasKo.map(c => {
                            const mm = c.mata_mata;
                            return `<div class="categoria-card">
                                <div class="categoria-head">
                                    <div class="categoria-title-wrap">
                                        <h3>${escapeHtml(c.categoria)}</h3>
                                        <p class="categoria-subtitle">${mm.rodadas.length} rodada(s) no mata-mata</p>
                                    </div>
                                    <div class="categoria-meta">
                                        <span class="categoria-badge">${mm.total_jogadores} jogador(es)</span>
                                        <span class="categoria-badge">Chave ${mm.tamanho_chave}</span>
                                    </div>
                                </div>
                                ${mm.campeao ? `<div class="campeao-highlight"><div class="campeao-label"><i class="fas fa-crown"></i> Campeão</div>${renderizarPartidaJogador(mm.campeao)}</div>` : ''}
                                <div class="rodadas-grid">
                                    ${mm.rodadas.map(rodada => `
                                        <div class="rodada-card">
                                            <div class="rodada-badge">${escapeHtml(rodada.nome)}</div>
                                            ${rodada.partidas.map(p => renderizarPartida(p)).join('')}
                                        </div>`).join('')}
                                </div>
                            </div>`;
                        }).join('')}</div>`;
                    } else if (!torneio.tem_grupos) {
                        kkContainer.innerHTML = '<p class="chaveamento-vazio">Gere a fase de grupos para iniciar o torneio.</p>';
                    } else {
                        kkContainer.innerHTML = '';
                    }
                })
                .catch(error => {
                    console.error('Erro ao carregar torneio:', error);
                    document.getElementById('chaveamento-container').innerHTML =
                        `<p style="color:red;padding:20px;">Erro ao carregar torneio: ${error.message}</p>`;
                });
        }

        function carregarChaveamento() { carregarTorneio(); }

        function adicionarJogadorInscrito() {
            const nomeInput = document.getElementById('nome-jogador');
            const categoriaInput = document.getElementById('categoria-jogador');
            const nivelInput = document.getElementById('nivel-jogador');
            const nome = nomeInput.value.trim();
            const categoria = categoriaInput.value;
            const nivel = nivelInput.value;
            
            if (!nome) {
                alert('Digite o nome do jogador');
                return;
            }

            fetch(`/api/campeonatos/${campeonatoId}/jogadores-inscritos`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ nome: nome, categoria: categoria, nivel: nivel })
            })
            .then(response => {
                if (!response.ok) throw new Error('Erro ao adicionar jogador');
                return response.json();
            })
            .then(jogador => {
                nomeInput.value = '';
                categoriaInput.value = 'Geral';
                nivelInput.value = 'iniciante';
                carregarJogadoresInscritos();
                console.log('✅ Jogador adicionado:', jogador);
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Erro ao adicionar jogador');
            });
        }

        function removerJogadorInscrito(jogadorId) {
            if (!confirm('Tem certeza que deseja remover este jogador?')) return;

            fetch(`/api/campeonatos/${campeonatoId}/jogadores-inscritos/${jogadorId}`, {
                method: 'DELETE'
            })
            .then(response => {
                if (!response.ok) throw new Error('Erro ao remover jogador');
                carregarJogadoresInscritos();
                console.log('✅ Jogador removido');
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Erro ao remover jogador');
            });
        }

        function criarMesa() {
            const numero = document.getElementById('numero-mesa').value;
            
            if (!numero) {
                alert('Digite um número para a mesa');
                return;
            }

            fetch('/api/mesas', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    campeonato_id: campeonatoId,
                    numero: parseInt(numero)
                })
            })
            .then(response => response.json())
            .then(mesa => {
                if (mesa.id) {
                    document.getElementById('numero-mesa').value = '';
                    carregarMesas();
                } else {
                    alert('Erro: ' + (mesa.erro || 'Desconhecido'));
                }
            })
            .catch(error => {
                console.error('Erro ao criar mesa:', error);
                alert('Erro ao criar mesa');
            });
        }

        function adicionarJogador(mesaId) {
            const jogadorInscritoId = document.getElementById(`jogador-${mesaId}`).value;
            const time = document.getElementById(`time-${mesaId}`).value;

            if (!jogadorInscritoId) {
                alert('Selecione um jogador');
                return;
            }

            const jogadorSelecionado = jogadoresDisponiveisParaMesas.find(jogador => String(jogador.id) === jogadorInscritoId);
            if (!jogadorSelecionado) {
                alert('Jogador selecionado não está mais disponível');
                carregarMesas();
                return;
            }

            fetch('/api/jogadores', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    mesa_id: mesaId,
                    nome: jogadorSelecionado.nome,
                    time: parseInt(time),
                    jogador_inscrito_id: parseInt(jogadorInscritoId)
                })
            })
            .then(response => response.json())
            .then(jogador => {
                if (jogador.id) {
                    document.getElementById(`jogador-${mesaId}`).value = '';
                    buscaDigitadaPorMesa[mesaId] = '';
                    carregarMesas();
                } else {
                    alert('Erro: ' + (jogador.erro || 'Desconhecido'));
                }
            })
            .catch(error => {
                console.error('Erro ao adicionar jogador:', error);
                alert('Erro ao adicionar jogador');
            });
        }

        function removerJogador(jogadorId) {
            if (!confirm('Remover este jogador?')) return;

            fetch(`/api/jogadores/${jogadorId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                carregarMesas();
            })
            .catch(error => {
                console.error('Erro ao remover jogador:', error);
                alert('Erro ao remover jogador');
            });
        }

        function deletarMesa(mesaId) {
            if (!confirm('Tem certeza que deseja deletar esta mesa?')) return;

            fetch(`/api/mesas/${mesaId}`, {
                method: 'DELETE'
            })
            .then(response => response.json())
            .then(data => {
                carregarMesas();
            })
            .catch(error => {
                console.error('Erro ao deletar mesa:', error);
                alert('Erro ao deletar mesa');
            });
        }

        function abrirControle(mesaId) {
            const modal = document.getElementById('modalControle');
            const qrcodeContainer = document.getElementById('qrcodeContainer');
            const abrirControleBtn = document.getElementById('abrirControleBtn');
            
            // Remover inline styles para permitir que as classes CSS funcionem
            modal.style.display = '';
            modal.style.opacity = '';
            
            // Limpar QR code anterior
            qrcodeContainer.innerHTML = '';
            
            // Criar novo QR code
            const protocolo = window.location.protocol;
            const host = window.location.host;
            const urlControle = `${protocolo}//${host}/controle/${mesaId}`;
            
            new QRCode(qrcodeContainer, {
                text: urlControle,
                width: 200,
                height: 200,
                colorDark: '#000000',
                colorLight: '#ffffff',
                correctLevel: QRCode.CorrectLevel.H
            });
            
            // Armazenar mesaId para usar depois
            abrirControleBtn.onclick = function() {
                abrirControleLink(mesaId);
            };
            
            // Mostrar modal
            console.log('Abrindo modal do QR code para mesa', mesaId);
            modal.classList.add('show');
        }

        function fecharModalControle() {
            const modal = document.getElementById('modalControle');
            if (modal) {
                console.log('Fechando modal QR code');
                modal.classList.remove('show');
                // Garantir que os inline styles não sobrescrevem as classes
                modal.style.opacity = '';
                modal.style.pointerEvents = '';
            }
        }

        function abrirControleLink(mesaId) {
            window.open(`/controle/${mesaId}`, '_blank');
        }

        function abrirPlacarMesa(mesaId) {
            window.location.href = `/placar-mesa/${mesaId}?campeonato_id=${campeonatoId}`;
        }

        // Fechar modal ao clicar fora dela ou no botão close
        window.onclick = function(event) {
            const modal = document.getElementById('modalControle');
            // Fechar ao clicar no overlay (fundo preto)
            if (event.target === modal) {
                fecharModalControle();
            }
        }

        // Melhorar listener de teclado para ESC
        document.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                const modal = document.getElementById('modalControle');
                if (modal && modal.classList.contains('show')) {
                    fecharModalControle();
                }
                const modalQR = document.getElementById('modalQRPrint');
                if (modalQR && modalQR.classList.contains('show')) {
                    fecharQRPrint();
                }
            }
        });

        function abrirQRPrint(mesaId, mesaNumero) {
            const modal = document.getElementById('modalQRPrint');
            const placarContainer = document.getElementById('qrPrintPlacar');
            const controleContainer = document.getElementById('qrPrintControle');
            
            modal.style.display = '';
            modal.style.opacity = '';
            
            placarContainer.innerHTML = '';
            controleContainer.innerHTML = '';
            
            const baseUrl = window.location.origin;
            const placarUrl = `${baseUrl}/placar-mesa/${mesaId}`;
            const controleUrl = `${baseUrl}/controle/${mesaId}`;
            
            document.getElementById('qr-print-mesa-numero').textContent = mesaNumero;
            document.getElementById('qr-print-placar-url').textContent = placarUrl;
            document.getElementById('qr-print-controle-url').textContent = controleUrl;
            
            const qrSize = Math.min(150, Math.floor((window.innerHeight - 300) / 2));
            new QRCode(placarContainer, {
                text: placarUrl,
                width: qrSize,
                height: qrSize,
                colorDark: '#1a1a2e',
                colorLight: '#ffffff',
                correctLevel: QRCode.CorrectLevel.H
            });
            new QRCode(controleContainer, {
                text: controleUrl,
                width: qrSize,
                height: qrSize,
                colorDark: '#9c27b0',
                colorLight: '#ffffff',
                correctLevel: QRCode.CorrectLevel.H
            });
            
            modal.classList.add('show');
        }

        function fecharQRPrint() {
            const modal = document.getElementById('modalQRPrint');
            if (modal) {
                modal.classList.remove('show');
                modal.style.opacity = '';
                modal.style.pointerEvents = '';
            }
        }

        function imprimirQR() {
            window.print();
        }
