let mesaId = window.APP_CONFIG ? window.APP_CONFIG.mesaId : null;
        let socket = io();
        let ultimoTimeComPonto = null;
        let jogoFinalizado = false;  // Flag para rastrear se o jogo terminou
        let mesa = null;  // Variável global para armazenar dados da mesa
        let jogadoresInscritos = [];  // Lista de jogadores inscritos no campeonato
        let nomesEmOutrasMesas = new Set();  // Nomes de jogadores já em outras mesas
        let mesasDisponiveis = [];  // Lista de mesas do campeonato
        let ladosInvertidos = false;
        let statusTimeoutId = null;

        socket.on('connect', function() {
            console.log('Conectado ao servidor');
            inscreverNaMesa(mesaId);
            carregarMesa();
        });

        function inscreverNaMesa(id) {
            console.log('📡 Inscrevendo controle na mesa:', id);
            socket.emit('inscrever_mesa', { mesa_id: id });
            socket.emit('controle_aberto', { mesa_id: id });
        }

        socket.on('placar_atualizado', function(data) {
            if (data.mesa_id === mesaId) {
                atualizarDisplay(data.placar);
            }
        });

        socket.on('jogadores_atualizados', function(data) {
            console.log('🔔 Evento jogadores_atualizados recebido no controle:', data);
            if (data.mesa_id === mesaId) {
                console.log('👥 Jogadores atualizados - recarregando mesa');
                carregarMesa();
            }
        });

        function getTimeNoLado(lado) {
            return ladosInvertidos ? (lado === 1 ? 2 : 1) : lado;
        }

        function obterJogadoresDoTime(time) {
            if (!mesa || !mesa.jogadores) return [];
            return mesa.jogadores.filter(j => j.time === time);
        }

        function obterNomeDoTime(time) {
            const jogadores = obterJogadoresDoTime(time);
            return jogadores.length > 0 ? jogadores.map(j => j.nome).join(' & ') : `Time ${time}`;
        }

        function renderizarNomesTimesPorLado() {
            const nomeNoLado1 = obterNomeDoTime(getTimeNoLado(1));
            const nomeNoLado2 = obterNomeDoTime(getTimeNoLado(2));

            document.getElementById('nome-time-1').innerHTML = `<i class="fas fa-users" style="margin-right: 8px;"></i>${nomeNoLado1}<button class="btn-editar-jogadores" onclick="abrirEditarJogadoresPorLado(1)" title="Editar jogadores"><i class="fas fa-edit"></i></button>`;
            document.getElementById('nome-time-2').innerHTML = `<i class="fas fa-users" style="margin-right: 8px;"></i>${nomeNoLado2}<button class="btn-editar-jogadores" onclick="abrirEditarJogadoresPorLado(2)" title="Editar jogadores"><i class="fas fa-edit"></i></button>`;

            const labelMini1 = document.getElementById('label-mini-lado-1');
            const labelMini2 = document.getElementById('label-mini-lado-2');
            if (labelMini1) labelMini1.textContent = nomeNoLado1;
            if (labelMini2) labelMini2.textContent = nomeNoLado2;
        }

        function atualizarEstadoAutoLados(placar) {
            const btn = document.getElementById('btn-auto-lados');
            if (!btn) return;

            const ativo = !!(placar && placar.auto_troca_lados_set);
            btn.innerHTML = `<i class="fas fa-repeat"></i> Auto Lados: ${ativo ? 'ON' : 'OFF'}`;
            btn.style.background = ativo
                ? 'linear-gradient(135deg, #43a047, #2e7d32)'
                : 'linear-gradient(135deg, #607d8b, #455a64)';
        }

        function atualizarMensagemPausa(statusPlacar) {
            const statusText = document.getElementById('status-text');
            if (!statusText) return;

            const mesaPausada = mesa && mesa.status === 'pausada';
            const placarPausado = statusPlacar === 'pausado';
            if (mesaPausada || placarPausado) {
                statusText.textContent = '⏸ Jogo pausado: não pode alterar os pontos';
            }
        }

        function mostrarMensagemJogoPausado() {
            const statusText = document.getElementById('status-text');
            if (!statusText) return;
            statusText.textContent = '⏸ Jogo pausado: não pode alterar os pontos';
        }

        function atualizarEstadoBotoesPonto(statusPlacar) {
            const btnIniciar = document.getElementById('btn-iniciar-jogo');
            const iniciarAtivo = !!(btnIniciar && !btnIniciar.disabled);
            const desabilitar = mesaOuPlacarEstaPausado(statusPlacar) || iniciarAtivo;
            const btnLado1 = document.getElementById('btn-ponto-lado-1');
            const btnLado2 = document.getElementById('btn-ponto-lado-2');

            if (btnLado1) btnLado1.disabled = desabilitar;
            if (btnLado2) btnLado2.disabled = desabilitar;
        }

        function mesaOuPlacarEstaPausado(statusPlacar) {
            const mesaPausada = mesa && mesa.status === 'pausada';
            const placarPausado = statusPlacar === 'pausado'
                || (mesa && mesa.placar && mesa.placar.status === 'pausado');
            return !!(mesaPausada || placarPausado);
        }

        function setStatusTemporario(texto, ms) {
            const statusText = document.getElementById('status-text');
            if (!statusText) return;

            if (statusTimeoutId) {
                clearTimeout(statusTimeoutId);
                statusTimeoutId = null;
            }

            statusText.textContent = texto;
            statusTimeoutId = setTimeout(() => {
                if (mesaOuPlacarEstaPausado()) {
                    atualizarMensagemPausa(mesa && mesa.placar ? mesa.placar.status : null);
                    return;
                }
                statusText.textContent = '✔ Pronto';
            }, ms);
        }

        function abrirEditarJogadoresPorLado(lado) {
            abrirEditarJogadores(getTimeNoLado(lado));
        }

        function carregarMesa() {
            fetch(`/api/mesas/${mesaId}`)
                .then(response => response.json())
                .then(mesaData => {
                    mesa = mesaData;  // Armazenar na variável global
                    document.getElementById('mesa-info').textContent = `Mesa ${mesa.numero}`;
                    
                    // Carregar jogadores inscritos do campeonato
                    fetch(`/api/campeonatos/${mesa.campeonato_id}/jogadores-inscritos`)
                        .then(res => res.json())
                        .then(jogadores => {
                            jogadoresInscritos = jogadores;
                            console.log('✅ Jogadores inscritos carregados:', jogadoresInscritos);
                        })
                        .catch(err => console.error('Erro ao carregar jogadores inscritos:', err));
                    
                    // Carregar mesas do campeonato para saber quais jogadores já estão ocupados
                    fetch(`/api/campeonatos/${mesa.campeonato_id}/mesas`)
                        .then(res => res.json())
                        .then(mesas => {
                            nomesEmOutrasMesas = new Set();
                            mesas.forEach(m => {
                                if (m.id !== mesaId) {
                                    m.jogadores.forEach(j => nomesEmOutrasMesas.add(j.nome));
                                }
                            });
                            console.log('✅ Jogadores em outras mesas:', nomesEmOutrasMesas);
                            
                            // Atualizar selector de mesas
                            mesasDisponiveis = mesas;
                            atualizarSelectorMesas(mesas);
                        })
                        .catch(err => console.error('Erro ao carregar mesas:', err));

                    ladosInvertidos = !!(mesa.placar && mesa.placar.lados_invertidos);
                    renderizarNomesTimesPorLado();
                    
                    if (mesa.placar) {
                        atualizarDisplay(mesa.placar);
                        atualizarEstadoAutoLados(mesa.placar);
                        atualizarEstadoBotoesPonto(mesa.placar.status);
                        
                        // Atualizar o select de formato
                        const formato = mesa.placar.formato_jogo || 'melhor_de_3';
                        document.getElementById('formato-select').value = formato;
                    }

                    atualizarMensagemPausa(mesa.placar ? mesa.placar.status : null);
                    if (!(mesa.status === 'pausada' || (mesa.placar && mesa.placar.status === 'pausado'))) {
                        document.getElementById('status-text').textContent = '\u2714 Pronto';
                    }
                })
                .catch(error => {
                    console.error('Erro ao carregar mesa:', error);
                    document.getElementById('mesa-info').textContent = 'Erro ao carregar';
                });
        }

        function atualizarDisplay(placar) {
            console.log('Atualizando display com placar:', placar);

            ladosInvertidos = !!placar.lados_invertidos;
            renderizarNomesTimesPorLado();

            const timeNoLado1 = getTimeNoLado(1);
            const timeNoLado2 = getTimeNoLado(2);
            const pontosLado1 = timeNoLado1 === 1 ? placar.pontos_time1 : placar.pontos_time2;
            const pontosLado2 = timeNoLado2 === 1 ? placar.pontos_time1 : placar.pontos_time2;
            
            const setAnterior = window.setAnteriorGlobal || null;
            window.setAnteriorGlobal = placar.set_numero;
            
            document.getElementById('pontos-1').textContent = pontosLado1;
            document.getElementById('pontos-2').textContent = pontosLado2;
            
            // Atualiza informações ITTF
            document.getElementById('set-numero').textContent = placar.set_numero || 1;
            
            // Se o set mudou, força reset dos saques
            let servesNoSet = placar.serves_no_set || 0;
            if (setAnterior !== null && setAnterior !== placar.set_numero) {
                console.log(`✨ SET MUDOU! ${setAnterior} → ${placar.set_numero}. Resetando saques.`);
                servesNoSet = 0; // Force reset quando set muda
            }
            
            // Atualiza indicador de sacador
            const servidorLabel = document.getElementById('servidor-label');
            const serveCount = (servesNoSet || 0) + 1;
            const ladoSacador = placar.servidor_time === timeNoLado1 ? 1 : 2;
            const serverClass = ladoSacador === 1 ? 'servidor-time1' : 'servidor-time2';
            const timeText = ladoSacador === 1 ? obterNomeDoTime(timeNoLado1) : obterNomeDoTime(timeNoLado2);
            
            console.log(`Sacador: Time ${placar.servidor_time}, Saques: ${servesNoSet}/1 (display: ${serveCount}/2)`);
            
            servidorLabel.innerHTML = `<i class="fas fa-circle-notch ${serverClass}"></i> ${timeText}`;
            document.getElementById('serves-count').textContent = `${serveCount}/2`;
            
            // Atualiza select de formato
            if (placar.formato_jogo) {
                document.getElementById('formato-select').value = placar.formato_jogo;
            }

            atualizarEstadoAutoLados(placar);
            if (mesa) {
                mesa.placar = placar;
            }
            atualizarEstadoBotoesPonto(placar.status);
            atualizarMensagemPausa(placar.status);
        }

        function adicionarPontoNoLado(lado) {
            const time = getTimeNoLado(lado);
            adicionarPonto(time);
        }

        function adicionarPonto(time) {
            // Se o jogo já terminou, mostrar a modal novamente
            if (jogoFinalizado) {
                console.log('⚠️ Jogo já terminou! Inicie um novo jogo para continuar.');
                document.getElementById('modal-vencedor').classList.add('active');
                return;
            }

            // Bloqueio imediato no front para feedback claro ao usuário.
            if (mesaOuPlacarEstaPausado()) {
                mostrarMensagemJogoPausado();
                return;
            }

            fetch(`/api/placar/mesa/${mesaId}/adicionar-ponto`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ time: time })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.placar) {
                    throw new Error(data.erro || 'Não foi possível adicionar ponto');
                }

                ultimoTimeComPonto = time;
                console.log('Resposta adicionar ponto:', data);
                
                // Atualiza o display
                atualizarDisplay(data.placar);
                
                // Se set foi finalizado
                if (data.set_info) {
                    console.log('✓ SET FINALIZADO! Zeit vencedor:', data.set_info.vencedor);
                    console.log('Sets agora:', `${data.set_info.sets_time1} x ${data.set_info.sets_time2}`);
                }
                
                // Se jogo foi finalizado
                if (data.jogo_info && data.jogo_info.jogo_finalizado) {
                    console.log('🏆 JOGO FINALIZADO! Time vencedor:', data.jogo_info.vencedor);
                    jogoFinalizado = true;  // Setar flag para bloquear novos pontos
                    mostrarModalVencedor(data.jogo_info);
                }
                
                // Se novo set começou
                if (data.proximo_set) {
                    console.log('→ NOVO SET COMEÇANDO:', data.proximo_set.set_numero);
                    console.log('Servidor inicia: Time', data.proximo_set.servidor_comeca);
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                if ((error.message || '').includes('Mesa em pausa')) {
                    mostrarMensagemJogoPausado();
                    return;
                }
                setStatusTemporario(`⚠ ${error.message}`, 2200);
            });
        }

        function removerPonto(time) {
            fetch(`/api/placar/mesa/${mesaId}/remover-ponto`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ time: time })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.placar) {
                    throw new Error(data.erro || 'Não foi possível remover ponto');
                }
                atualizarDisplay(data.placar);
            })
            .catch(error => {
                console.error('Erro:', error);
                if ((error.message || '').includes('Mesa em pausa')) {
                    mostrarMensagemJogoPausado();
                    return;
                }
                setStatusTemporario(`⚠ ${error.message}`, 2200);
            });
        }

        function removerUltimoPonto() {
            if (!ultimoTimeComPonto) {
                alert('Nenhum ponto foi adicionado ainda');
                return;
            }

            fetch(`/api/placar/mesa/${mesaId}/remover-ponto`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ time: ultimoTimeComPonto })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.placar) {
                    throw new Error(data.erro || 'Não foi possível desfazer ponto');
                }
                atualizarDisplay(data.placar);
            })
            .catch(error => {
                console.error('Erro:', error);
                if ((error.message || '').includes('Mesa em pausa')) {
                    mostrarMensagemJogoPausado();
                    return;
                }
                setStatusTemporario(`⚠ ${error.message}`, 2200);
            });
        }

        function resetarPlacar() {
            if (!confirm('Tem certeza que deseja resetar o jogo?\n\nTodos os sets, pontos e contadores serão zerados!')) return;

            fetch(`/api/mesas/${mesaId}/resetar`, {
                method: 'POST'
            })
            .then(response => response.json())
            .then(placar => {
                atualizarDisplay(placar);
                setStatusTemporario('Jogo resetado para zero!', 3000);
            })
            .catch(error => console.error('Erro:', error));
        }

        function iniciarJogo() {
            if (!mesa) {
                alert('❌ Mesa não carregada ainda. Aguarde...');
                return;
            }

            if (mesa.jogadores.length < 2) {
                alert('❌ É necessário pelo menos 2 jogadores (um por time) para iniciar o jogo!\n\nAdicione os jogadores antes de iniciar.');
                return;
            }

            // Desabilitar botão enquanto processa
            const btnIniciar = document.getElementById('btn-iniciar-jogo');
            btnIniciar.disabled = true;
            btnIniciar.classList.add('desativado');

            fetch(`/api/placar/mesa/${mesaId}/iniciar-jogo`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => {
                        throw new Error(err.erro || 'Erro ao iniciar jogo');
                    });
                }
                return response.json();
            })
            .then(data => {
                console.log('✅ Jogo iniciado com sucesso!', data);
                atualizarDisplay(data.placar);
                if (mesa) {
                    mesa.status = 'em_uso';
                    mesa.placar = data.placar;
                }
                atualizarEstadoBotoesPonto(data.placar ? data.placar.status : null);
                setStatusTemporario('🎮 Jogo iniciado!', 3000);
                jogoFinalizado = false;
                
                // Habilitar botão pausar e os outros botões
                document.getElementById('btn-pausar-jogo').disabled = false;
                document.getElementById('btn-resetar').disabled = false;
                document.getElementById('btn-trocar').disabled = false;
                document.getElementById('btn-trocar-lados').disabled = false;
                document.getElementById('btn-auto-lados').disabled = false;
                document.getElementById('btn-desfazer').disabled = false;
                
            })
            .catch(error => {
                console.error('Erro ao iniciar jogo:', error);
                alert('❌ Erro: ' + error.message);
                // Re-habilitar botão em caso de erro
                btnIniciar.disabled = false;
                btnIniciar.classList.remove('desativado');
            });
        }

        function pausarJogo() {
            const btnPausar = document.getElementById('btn-pausar-jogo');
            btnPausar.disabled = true;

            // Atualizar status da mesa para pausada
            fetch(`/api/mesas/${mesaId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'pausada' })
            }).catch(err => console.error('Erro ao atualizar status da mesa:', err));

            // Atualizar status do placar para pausado
            fetch(`/api/placar/mesa/${mesaId}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'pausado' })
            })
            .then(response => {
                if (!response.ok) {
                    return response.json().then(err => { throw new Error(err.erro || 'Erro ao pausar'); });
                }
                return response.json();
            })
            .then(data => {
                console.log('⏸ Jogo pausado!', data);
                if (mesa) mesa.status = 'pausada';
                if (mesa) mesa.placar = data;
                atualizarEstadoBotoesPonto(data.status);
                mostrarMensagemJogoPausado();
                
                // Habilitar Iniciar Jogo (para retomar)
                const btnIniciar = document.getElementById('btn-iniciar-jogo');
                btnIniciar.disabled = false;
                btnIniciar.classList.remove('desativado');
                
                // Desabilitar demais botões
                document.getElementById('btn-resetar').disabled = true;
                document.getElementById('btn-trocar').disabled = true;
                document.getElementById('btn-trocar-lados').disabled = true;
                document.getElementById('btn-auto-lados').disabled = true;
                document.getElementById('btn-desfazer').disabled = true;
            })
            .catch(error => {
                console.error('Erro ao pausar jogo:', error);
                alert('❌ Erro: ' + error.message);
                btnPausar.disabled = false;
            });
        }

        function trocarSacador() {
            // Se o jogo já terminou, mostrar a modal novamente
            if (jogoFinalizado) {
                console.log('⚠️ Jogo já terminou! Inicie um novo jogo para continuar.');
                document.getElementById('modal-vencedor').classList.add('active');
                return;
            }

            fetch(`/api/placar/mesa/${mesaId}/trocar-sacador`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.sucesso) {
                    atualizarDisplay(data.placar);
                    console.log(data.mensagem);
                } else {
                    alert('Erro: ' + data.erro);
                }
            })
            .catch(error => {
                console.error('Erro ao trocar sacador:', error);
                alert('Erro ao trocar sacador');
            });
        }

        function trocarLadosMesa() {
            fetch(`/api/placar/mesa/${mesaId}/trocar-lados`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.sucesso) {
                    ladosInvertidos = !!data.placar.lados_invertidos;
                    atualizarDisplay(data.placar);
                    document.getElementById('status-text').textContent = ladosInvertidos
                        ? 'Lados invertidos no placar'
                        : 'Lados normalizados no placar';
                    setTimeout(() => {
                        document.getElementById('status-text').textContent = '✔ Pronto';
                    }, 2200);
                } else {
                    alert('Erro: ' + data.erro);
                }
            })
            .catch(error => {
                console.error('Erro ao trocar lados:', error);
                alert('Erro ao trocar lados');
            });
        }

        function toggleAutoTrocaLadosSet() {
            fetch(`/api/placar/mesa/${mesaId}/toggle-auto-troca-lados`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.sucesso) {
                    atualizarDisplay(data.placar);
                    atualizarEstadoAutoLados(data.placar);
                    document.getElementById('status-text').textContent = data.mensagem;
                    setTimeout(() => {
                        document.getElementById('status-text').textContent = '✔ Pronto';
                    }, 2200);
                } else {
                    alert('Erro: ' + data.erro);
                }
            })
            .catch(error => {
                console.error('Erro ao alternar auto troca de lados:', error);
                alert('Erro ao alternar auto troca de lados');
            });
        }

        function mostrarModalVencedor(jogoInfo) {
            const nomeExibido = obterNomeDoTime(jogoInfo.vencedor);
            const score = `${jogoInfo.sets_finais.time1} × ${jogoInfo.sets_finais.time2}`;
            
            document.getElementById('modal-vencedor-nome').textContent = nomeExibido;
            document.getElementById('modal-vencedor-score').textContent = `${score} sets`;
            document.getElementById('modal-vencedor').classList.add('active');
        }

        function fecharModalVencedor() {
            document.getElementById('modal-vencedor').classList.remove('active');
        }

        function resetarEstadoBotoes() {
            // Mostrar e habilitar o botão "Iniciar Jogo"
            const btnIniciar = document.getElementById('btn-iniciar-jogo');
            btnIniciar.style.display = '';
            btnIniciar.disabled = false;
            btnIniciar.classList.remove('desativado');

            // Com o iniciar ativo, botões de ponto devem ficar desabilitados
            atualizarEstadoBotoesPonto(mesa && mesa.placar ? mesa.placar.status : null);
            
            // Desabilitar pausar e os outros botões
            document.getElementById('btn-pausar-jogo').disabled = true;
            document.getElementById('btn-resetar').disabled = true;
            document.getElementById('btn-trocar').disabled = true;
            document.getElementById('btn-trocar-lados').disabled = true;
            document.getElementById('btn-auto-lados').disabled = true;
            document.getElementById('btn-desfazer').disabled = true;
            
            // Resetar flag de jogo finalizado
            jogoFinalizado = false;
        }

        function voltarPaginaAnterior() {
            const btnFechar = document.getElementById('btn-fechar');
            if (btnFechar) btnFechar.disabled = true;

            fetch(`/api/placar/mesa/${mesaId}/reset`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (!data.sucesso) {
                    throw new Error(data.erro || 'Não foi possível resetar a mesa');
                }

                if (mesa && mesa.campeonato_id) {
                    window.location.href = `/campeonato/${mesa.campeonato_id}`;
                } else {
                    window.location.href = '/';
                }
            })
            .catch(error => {
                console.error('Erro ao fechar e resetar mesa:', error);
                alert('Erro ao resetar a mesa antes de fechar. Tente novamente.');
                if (btnFechar) btnFechar.disabled = false;
            });
        }

        function liberarMesa() {
            // Fecha a modal de vencedor
            document.getElementById('modal-vencedor').classList.remove('active');
            
            // Faz requisição para resetar a mesa
            fetch(`/api/placar/mesa/${mesaId}/reset`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.sucesso) {
                    console.log('Mesa resetada com sucesso');
                    // Atualizar o display local
                    atualizarDisplay(data.placar);
                    // Resetar estado dos botões
                    resetarEstadoBotoes();
                } else {
                    alert('Erro: ' + data.erro);
                }
            })
            .catch(error => {
                console.error('Erro ao resetar mesa:', error);
                alert('Erro ao resetar mesa');
            });
        }

        function iniciarNovoJogo() {
            document.getElementById('modal-vencedor').classList.remove('active');
            // Carregar mesa antes de abrir o modal de edição
            fetch(`/api/mesas/${mesaId}`)
                .then(response => response.json())
                .then(mesaData => {
                    mesa = mesaData; // Atualizar variável global mesa
                    // Resetar estado dos botões
                    resetarEstadoBotoes();
                    abrirEditarJogadoresModal();
                })
                .catch(error => {
                    console.error('Erro ao carregar mesa:', error);
                    alert('Erro ao carregar dados da mesa');
                });
        }

        let timeEmEdicao = null;

        function popularSelectJogadores(selectElement, nomeAtual, opcional) {
            const defaultLabel = opcional ? '-- Nenhum --' : '-- Selecione um jogador --';
            selectElement.innerHTML = `<option value="">${defaultLabel}</option>`;
            
            // Nomes dos jogadores da mesa atual (para permitir que continuem selecionáveis)
            const nomesDaMesaAtual = new Set(mesa.jogadores.map(j => j.nome));
            
            jogadoresInscritos.forEach(jogador => {
                // Mostrar se: é o jogador atual, está na mesa atual, ou não está em nenhuma outra mesa
                const estaEmOutraMesa = nomesEmOutrasMesas.has(jogador.nome);
                if (estaEmOutraMesa && jogador.nome !== nomeAtual) return;
                
                const option = document.createElement('option');
                option.value = jogador.nome;
                option.textContent = jogador.nome;
                if (jogador.nome === nomeAtual) {
                    option.selected = true;
                }
                selectElement.appendChild(option);
            });
        }

        function abrirEditarJogadores(time) {
            timeEmEdicao = time;
            const modal = document.getElementById('modal-edit-jogadores');
            const jogadores = mesa.jogadores.filter(j => j.time === time);
            
            // Popular selects com jogadores inscritos
            const select1 = document.getElementById('jogador1-select');
            const select2 = document.getElementById('jogador2-select');
            
            popularSelectJogadores(select1, jogadores.length > 0 ? jogadores[0].nome : '');
            popularSelectJogadores(select2, jogadores.length > 1 ? jogadores[1].nome : '');
            
            if (jogadores.length > 1) {
                document.getElementById('jogador2-group').style.display = 'block';
            } else {
                document.getElementById('jogador2-group').style.display = 'none';
            }
            
            modal.classList.add('active');
            document.getElementById('jogador1-select').focus();
        }

        function fecharEditarJogadores() {
            document.getElementById('modal-edit-jogadores').classList.remove('active');
            timeEmEdicao = null;
        }

        function abrirEditarJogadoresModal() {
            // Abre modal especial para editar ambos os times após fim de jogo
            const modal = document.getElementById('modal-edit-ambos-times');
            const jogadores1 = mesa.jogadores.filter(j => j.time === 1);
            const jogadores2 = mesa.jogadores.filter(j => j.time === 2);
            
            // Popular selects com jogadores inscritos e selecionar o atual
            popularSelectJogadores(document.getElementById('time1-jogador1-select'), jogadores1[0]?.nome || '');
            popularSelectJogadores(document.getElementById('time1-jogador2-select'), jogadores1[1]?.nome || '', true);
            popularSelectJogadores(document.getElementById('time2-jogador1-select'), jogadores2[0]?.nome || '');
            popularSelectJogadores(document.getElementById('time2-jogador2-select'), jogadores2[1]?.nome || '', true);
            
            modal.classList.add('active');
            document.getElementById('time1-jogador1-select').focus();
        }

        function fecharEditarJogadoresModal() {
            document.getElementById('modal-edit-ambos-times').classList.remove('active');
        }

        function salvarAmbosOsJogadores() {
            const time1j1 = document.getElementById('time1-jogador1-select').value.trim();
            const time1j2 = document.getElementById('time1-jogador2-select').value.trim();
            const time2j1 = document.getElementById('time2-jogador1-select').value.trim();
            const time2j2 = document.getElementById('time2-jogador2-select').value.trim();
            
            if (!time1j1 || !time2j1) {
                alert('Por favor, insira o nome do jogador 1 de cada time');
                return;
            }
            
            // Salvar Time 1
            const nomes1 = [time1j1];
            if (time1j2) nomes1.push(time1j2);
            
            // Salvar Time 2
            const nomes2 = [time2j1];
            if (time2j2) nomes2.push(time2j2);
            
            Promise.all([
                fetch(`/api/mesas/${mesaId}/atualizar-jogadores`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ time: 1, nomes: nomes1 })
                }).then(r => r.json()),
                fetch(`/api/mesas/${mesaId}/atualizar-jogadores`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ time: 2, nomes: nomes2 })
                }).then(r => r.json())
            ])
            .then(([data1, data2]) => {
                if (data1.sucesso && data2.sucesso) {
                    // Após salvar os jogadores, resetar o placar
                    return fetch(`/api/mesas/${mesaId}/resetar`, {
                        method: 'POST'
                    }).then(r => r.json());
                } else {
                    throw new Error('Erro ao atualizar jogadores');
                }
            })
            .then(placar => {
                // Placar foi resetado com sucesso
                jogoFinalizado = false;  // Resetar flag quando novo jogo começa
                carregarMesa();
                fecharEditarJogadoresModal();
                atualizarDisplay(placar);
                document.getElementById('status-text').textContent = 'Novo jogo iniciado! Jogadores alterados e placar zerado.';
                setTimeout(() => {
                    document.getElementById('status-text').textContent = '✓ Pronto';
                }, 3000);
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Erro ao iniciar novo jogo');
            });
        }

        function salvarJogadores() {
            if (!timeEmEdicao) return;
            
            const jogador1 = document.getElementById('jogador1-select').value.trim();
            const jogador2 = document.getElementById('jogador2-select').value.trim();
            
            if (!jogador1) {
                alert('Por favor, selecione o jogador 1');
                return;
            }
            
            const nomes = [jogador1];
            if (jogador2) {
                nomes.push(jogador2);
            }
            
            fetch(`/api/mesas/${mesaId}/atualizar-jogadores`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ time: timeEmEdicao, nomes: nomes })
            })
            .then(response => response.json())
            .then(data => {
                if (data.sucesso) {
                    // Recarregar dados da mesa
                    carregarMesa();
                    fecharEditarJogadores();
                } else {
                    alert('Erro ao atualizar jogadores');
                }
            })
            .catch(error => {
                console.error('Erro:', error);
                alert('Erro ao atualizar jogadores');
            });
        }

        function alterarFormato() {
            const formatoSelect = document.getElementById('formato-select');
            const formato = formatoSelect.value;
            
            fetch(`/api/placar/mesa/${mesaId}/configurar-formato`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ formato_jogo: formato })
            })
            .then(response => response.json())
            .then(data => {
                if (data.sucesso) {
                    console.log(`📋 Formato alterado para: ${formato}`);
                    atualizarDisplay(data.placar);
                } else {
                    alert('Erro ao alterar formato: ' + data.erro);
                    // Reverter select para valor anterior
                    carregarMesa();
                }
            })
            .catch(error => {
                console.error('Erro ao alterar formato:', error);
                alert('Erro ao alterar formato do jogo');
            });
        }

        function atualizarSelectorMesas(mesas) {
            const select = document.getElementById('mesa-select');
            select.innerHTML = '';
            mesas.sort((a, b) => a.numero - b.numero).forEach(m => {
                const option = document.createElement('option');
                option.value = m.id;
                const jogNomes = m.jogadores.map(j => j.nome).join(' vs ');
                option.textContent = `Mesa ${m.numero}${jogNomes ? ' - ' + jogNomes : ''}`;
                if (m.id === mesaId) option.selected = true;
                select.appendChild(option);
            });
        }

        function trocarMesa(novaMesaId) {
            novaMesaId = parseInt(novaMesaId);
            if (novaMesaId === mesaId) return;

            // Desinscrever da mesa atual
            socket.emit('desinscrever_mesa', { mesa_id: mesaId });

            // Atualizar mesaId
            mesaId = novaMesaId;

            // Resetar estado
            ultimoTimeComPonto = null;
            jogoFinalizado = false;
            resetarEstadoBotoes();

            // Inscrever na nova mesa
            inscreverNaMesa(mesaId);

            // Carregar dados da nova mesa
            carregarMesa();

            // Atualizar URL sem recarregar a página
            window.history.replaceState(null, '', `/controle/${mesaId}`);

            document.getElementById('status-text').textContent = 'Trocando de mesa...';
            setTimeout(() => {
                document.getElementById('status-text').textContent = '✔ Pronto';
            }, 1500);
        }

        let qrGerado = false;
        let qrMesaAtual = null;
        function abrirQRCode() {
            const baseUrl = window.location.origin;
            const placarUrl = `${baseUrl}/placar-mesa/${mesaId}`;
            const controleUrl = `${baseUrl}/controle/${mesaId}`;
            const mesaNome = document.getElementById('mesa-info').textContent || `Mesa ${mesaId}`;
            
            document.getElementById('qr-mesa-nome').textContent = mesaNome;
            document.getElementById('qr-placar-url').textContent = placarUrl;
            document.getElementById('qr-controle-url').textContent = controleUrl;
            
            // Regenerar QR se mesa mudou
            if (qrGerado && qrMesaAtual !== mesaId) {
                document.getElementById('qr-placar').innerHTML = '';
                document.getElementById('qr-controle').innerHTML = '';
                qrGerado = false;
            }
            
            if (!qrGerado) {
                new QRCode(document.getElementById('qr-placar'), {
                    text: placarUrl,
                    width: 140,
                    height: 140,
                    colorDark: '#1a1a2e',
                    colorLight: '#ffffff'
                });
                new QRCode(document.getElementById('qr-controle'), {
                    text: controleUrl,
                    width: 140,
                    height: 140,
                    colorDark: '#0066cc',
                    colorLight: '#ffffff'
                });
                qrGerado = true;
                qrMesaAtual = mesaId;
            }
            
            document.getElementById('qr-modal').classList.add('active');
        }

        function fecharQRCode() {
            document.getElementById('qr-modal').classList.remove('active');
        }

        function imprimirQR() {
            window.print();
        }
