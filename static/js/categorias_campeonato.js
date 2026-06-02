        // ==================== FUNÇÕES DE CATEGORIAS ====================

        function carregarCategorias() {
            console.log(`📡 Carregando categorias para campeonato ${campeonatoId}...`);
            fetch(`/api/campeonatos/${campeonatoId}/categorias`)
                .then(response => response.json())
                .then(categorias => {
                    console.log('✅ Categorias carregadas:', categorias);
                    const container = document.getElementById('categorias-container');
                    const selectCategoria = document.getElementById('categoria-jogador');
                    
                    if (!container || !selectCategoria) return;
                    
                    // Limpar select de categorias
                    selectCategoria.innerHTML = '<option value="" selected disabled>Selecione uma categoria...</option>';
                    
                    // Renderizar badges de categorias
                    if (categorias.length === 0) {
                        container.innerHTML = '<p class="loading">Nenhuma categoria cadastrada. Crie uma para começar!</p>';
                    } else {
                        container.innerHTML = categorias.map(cat => `
                            <div class="categoria-badge">
                                <div class="categoria-info">
                                    <span class="categoria-nome">${escapeHtml(cat.nome)}</span>
                                    ${cat.descricao ? `<span class="categoria-desc">${escapeHtml(cat.descricao)}</span>` : ''}
                                </div>
                                <div class="categoria-acoes">
                                    <button class="categoria-btn" onclick="editarCategoria(${cat.id}, '${escapeHtml(cat.nome)}', '${escapeHtml(cat.descricao || '')}')">
                                        <i class="fas fa-edit"></i>
                                    </button>
                                    <button class="categoria-btn" onclick="deletarCategoria(${cat.id}, '${escapeHtml(cat.nome)}')">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </div>
                            </div>
                        `).join('');
                        
                        // Preencher select
                        categorias.forEach(cat => {
                            const option = document.createElement('option');
                            option.value = cat.id;
                            option.textContent = cat.nome;
                            selectCategoria.appendChild(option);
                        });
                    }
                })
                .catch(error => console.error('❌ Erro ao carregar categorias:', error));
        }

        function adicionarCategoria() {
            const nome = document.getElementById('nova-categoria-nome').value.trim();
            const descricao = document.getElementById('nova-categoria-descricao').value.trim();
            
            if (!nome) {
                alert('Por favor, insira o nome da categoria');
                return;
            }
            
            fetch(`/api/campeonatos/${campeonatoId}/categorias`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nome, descricao })
            })
            .then(response => {
                if (!response.ok) return response.json().then(e => Promise.reject(e));
                return response.json();
            })
            .then(categoria => {
                console.log('✅ Categoria criada:', categoria);
                alert(`Categoria "${categoria.nome}" criada com sucesso!`);
                document.getElementById('nova-categoria-nome').value = '';
                document.getElementById('nova-categoria-descricao').value = '';
                carregarCategorias();
            })
            .catch(error => {
                console.error('❌ Erro ao criar categoria:', error);
                alert(`Erro: ${error.erro || error.message || 'Falha ao criar categoria'}`);
            });
        }

        function editarCategoria(id, nomeAtual, descricaoAtual) {
            const novoNome = prompt('Novo nome da categoria:', nomeAtual);
            if (!novoNome || novoNome === nomeAtual) return;
            
            fetch(`/api/campeonatos/categorias/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ nome: novoNome, descricao: descricaoAtual })
            })
            .then(response => response.json())
            .then(categoria => {
                console.log('✅ Categoria atualizada:', categoria);
                alert(`Categoria atualizada para "${categoria.nome}"`);
                carregarCategorias();
            })
            .catch(error => {
                console.error('❌ Erro ao atualizar categoria:', error);
                alert(`Erro: ${error.erro || error.message}`);
            });
        }

        function deletarCategoria(id, nome) {
            if (!confirm(`Tem certeza que deseja deletar a categoria "${nome}"?`)) return;
            
            fetch(`/api/campeonatos/categorias/${id}`, { method: 'DELETE' })
            .then(response => response.json())
            .then(data => {
                console.log('✅ Categoria deletada:', data);
                alert(data.mensagem || 'Categoria deletada com sucesso');
                carregarCategorias();
            })
            .catch(error => {
                console.error('❌ Erro ao deletar categoria:', error);
                alert(`Erro: ${error.erro || error.message}`);
            });
        }

        function adicionarJogadorInscrito() {
            const nome = document.getElementById('nome-jogador').value.trim();
            const categoriaId = document.getElementById('categoria-jogador').value;
            const nivel = document.getElementById('nivel-jogador').value;
            
            if (!nome) {
                alert('Por favor, insira o nome do jogador');
                return;
            }
            
            if (!categoriaId) {
                alert('Por favor, selecione uma categoria');
                return;
            }
            
            fetch(`/api/campeonatos/${campeonatoId}/jogadores-inscritos`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    nome, 
                    categoria_id: parseInt(categoriaId),
                    nivel
                })
            })
            .then(response => response.json())
            .then(jogador => {
                console.log('✅ Jogador inscrito:', jogador);
                document.getElementById('nome-jogador').value = '';
                document.getElementById('categoria-jogador').value = '';
                document.getElementById('nivel-jogador').value = 'iniciante';
                carregarJogadoresInscritos();
            })
            .catch(error => {
                console.error('❌ Erro ao inscrever jogador:', error);
                alert(`Erro: ${error.erro || error.message}`);
            });
        }

        // Carregamento de categorias quando paginaJogadores é ativa
        // (socket.io já é inicializado em gerenciar_campeonato.js)
