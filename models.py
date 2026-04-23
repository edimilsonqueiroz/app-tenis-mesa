from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import UniqueConstraint

db = SQLAlchemy()

class Campeonato(db.Model):
    __tablename__ = 'campeonatos'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False, unique=True)
    descricao = db.Column(db.String(500))
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='ativo')  # ativo, pausado, finalizado
    
    mesas = db.relationship('Mesa', backref='campeonato', lazy=True, cascade='all, delete-orphan')
    jogadores_inscritos = db.relationship('JogadorInscrito', backref='campeonato', lazy=True, cascade='all, delete-orphan')
    partidas_chaveamento = db.relationship('ChaveamentoPartida', backref='campeonato', lazy=True, cascade='all, delete-orphan')
    grupos_chaveamento = db.relationship('GrupoChaveamento', backref='campeonato', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        try:
            mesas_count = len(self.mesas) if self.mesas else 0
        except Exception as e:
            print(f"[ERROR] Erro ao contar mesas: {e}")
            mesas_count = 0
        
        try:
            jogadores_count = len(self.jogadores_inscritos) if self.jogadores_inscritos else 0
        except Exception as e:
            print(f"[ERROR] Erro ao contar jogadores inscritos: {e}")
            jogadores_count = 0
        
        return {
            'id': self.id,
            'nome': self.nome,
            'descricao': self.descricao,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'status': self.status,
            'total_mesas': mesas_count,
            'total_jogadores': jogadores_count
        }


class JogadorInscrito(db.Model):
    __tablename__ = 'jogadores_inscritos'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(50), nullable=False, default='Geral')
    nivel = db.Column(db.String(20), nullable=False, default='iniciante')
    campeonato_id = db.Column(db.Integer, db.ForeignKey('campeonatos.id'), nullable=False)
    data_inscricao = db.Column(db.DateTime, default=datetime.utcnow)
    ativo = db.Column(db.Boolean, default=True)
    
    jogadores = db.relationship('Jogador', backref='jogador_inscrito', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'categoria': self.categoria,
            'nivel': self.nivel,
            'campeonato_id': self.campeonato_id,
            'data_inscricao': self.data_inscricao.isoformat() if self.data_inscricao else None,
            'ativo': self.ativo
        }


class Mesa(db.Model):
    __tablename__ = 'mesas'
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, nullable=False)
    campeonato_id = db.Column(db.Integer, db.ForeignKey('campeonatos.id'), nullable=False)
    status = db.Column(db.String(20), default='disponivel')  # disponivel, em_uso, pausada
    
    jogadores_mesa = db.relationship('JogadorMesa', backref='mesa', lazy=True, cascade='all, delete-orphan')
    placar = db.relationship('Placar', uselist=False, backref='mesa', cascade='all, delete-orphan')
    
    @property
    def jogadores(self):
        """Propriedade para acessar jogadores através de JogadorMesa"""
        return [jm.jogador for jm in self.jogadores_mesa]
    
    def to_dict(self):
        return {
            'id': self.id,
            'numero': self.numero,
            'campeonato_id': self.campeonato_id,
            'status': self.status,
            'jogadores': [j.to_dict_com_mesa() for j in self.jogadores_mesa],
            'placar': self.placar.to_dict() if self.placar else None
        }


class JogadorMesa(db.Model):
    """Tabela intermediária para vincular Jogador com Mesa"""
    __tablename__ = 'jogadores_mesa'
    
    id = db.Column(db.Integer, primary_key=True)
    jogador_id = db.Column(db.Integer, db.ForeignKey('jogadores.id'), nullable=False)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesas.id'), nullable=False)
    
    # Informações específicas do jogador nesta mesa
    time = db.Column(db.Integer, nullable=False)  # 1 ou 2 (para duplas/simples)
    sets_vencidos = db.Column(db.Integer, default=0)  # Contador de sets vencidos por este jogador
    pontos_marcados = db.Column(db.Integer, default=0)  # Total de pontos marcados pelo jogador
    
    jogador = db.relationship('Jogador', backref='mesas_vinculadas')
    
    def to_dict(self):
        """Retorna dados do jogador com informações da mesa"""
        return {
            'id': self.id,
            'jogador_id': self.jogador_id,
            'mesa_id': self.mesa_id,
            'nome': self.jogador.nome,
            'jogador_inscrito_id': self.jogador.jogador_inscrito_id,
            'time': self.time,
            'sets_vencidos': self.sets_vencidos,
            'pontos_marcados': self.pontos_marcados
        }
    
    def to_dict_simples(self):
        """Retorna dados simplificados"""
        return {
            'id': self.id,
            'nome': self.jogador.nome,
            'time': self.time,
            'sets_vencidos': self.sets_vencidos,
            'pontos_marcados': self.pontos_marcados
        }


class Jogador(db.Model):
    __tablename__ = 'jogadores'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    jogador_inscrito_id = db.Column(db.Integer, db.ForeignKey('jogadores_inscritos.id'), nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'jogador_inscrito_id': self.jogador_inscrito_id
        }
    
    def to_dict_com_mesa(self):
        """Retorna dados do jogador para exibição na mesa"""
        if self.mesas_vinculadas:
            jm = self.mesas_vinculadas[0]  # Pegando o primeiro vínculo (deve haver apenas um ativo)
            return {
                'id': self.id,
                'nome': self.nome,
                'jogador_mesa_id': jm.id,
                'mesa_id': jm.mesa_id,
                'jogador_inscrito_id': self.jogador_inscrito_id,
                'time': jm.time,
                'sets_vencidos': jm.sets_vencidos,
                'pontos_marcados': jm.pontos_marcados
            }
        return self.to_dict()


class ResultadoPartida(db.Model):
    __tablename__ = 'resultados_partidas'
    
    id = db.Column(db.Integer, primary_key=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesas.id'), nullable=True)
    campeonato_id = db.Column(db.Integer, db.ForeignKey('campeonatos.id'), nullable=False)
    
    # Nomes dos jogadores (armazenam mesmo após deletar da mesa)
    jogadores_time1 = db.Column(db.String(200), nullable=False)  # Nomes separados por " & "
    jogadores_time2 = db.Column(db.String(200), nullable=False)  # Nomes separados por " & "
    
    # Pontos e sets finais
    pontos_time1 = db.Column(db.Integer, default=0)
    pontos_time2 = db.Column(db.Integer, default=0)
    sets_time1 = db.Column(db.Integer, default=0)
    sets_time2 = db.Column(db.Integer, default=0)
    
    # Vencedor
    vencedor_time = db.Column(db.Integer)  # 1 ou 2
    
    # Data
    data_conclusao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'mesa_id': self.mesa_id,
            'campeonato_id': self.campeonato_id,
            'jogadores_time1': self.jogadores_time1,
            'jogadores_time2': self.jogadores_time2,
            'pontos_time1': self.pontos_time1,
            'pontos_time2': self.pontos_time2,
            'sets_time1': self.sets_time1,
            'sets_time2': self.sets_time2,
            'vencedor_time': self.vencedor_time,
            'data_conclusao': self.data_conclusao.isoformat() if self.data_conclusao else None
        }


class Placar(db.Model):
    __tablename__ = 'placares'
    
    id = db.Column(db.Integer, primary_key=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey('mesas.id'), nullable=False, unique=True)
    
    # Pontos do set atual
    pontos_time1 = db.Column(db.Integer, default=0)
    pontos_time2 = db.Column(db.Integer, default=0)
    
    # Rastreamento de sets (ITTF rules)
    set_numero = db.Column(db.Integer, default=1)  # Set atual (1, 2, 3, etc)
    sets_time1 = db.Column(db.Integer, default=0)  # Sets ganhos pelo time 1
    sets_time2 = db.Column(db.Integer, default=0)  # Sets ganhos pelo time 2
    servidor_inicial_jogo = db.Column(db.Integer, default=1)  # Time que começou sacando no Set 1 (para cálculos ITTF)
    
    # Rastreamento de sacador (server)
    servidor_time = db.Column(db.Integer, default=1)  # Qual time está sacando (1 ou 2)
    serves_no_set = db.Column(db.Integer, default=0)  # Quantos saques consecutivos (0-1, reseta a cada 2)
    lados_invertidos = db.Column(db.Boolean, default=False)  # Exibição espelhada: time1<->time2 nos lados
    
    # Configuração do formato do jogo (ITTF)
    formato_jogo = db.Column(db.String(20), default='melhor_de_3')  # melhor_de_3, melhor_de_5, melhor_de_7
    auto_troca_lados_set = db.Column(db.Boolean, default=False)  # Troca lados automaticamente ao iniciar novo set
    
    status = db.Column(db.String(20), default='em_andamento')  # em_andamento, pausado, finalizado
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'mesa_id': self.mesa_id,
            'pontos_time1': self.pontos_time1,
            'pontos_time2': self.pontos_time2,
            'set_numero': self.set_numero,
            'sets_time1': self.sets_time1,
            'sets_time2': self.sets_time2,
            'servidor_inicial_jogo': self.servidor_inicial_jogo,
            'servidor_time': self.servidor_time,
            'serves_no_set': self.serves_no_set,
            'lados_invertidos': self.lados_invertidos,
            'formato_jogo': self.formato_jogo,
            'auto_troca_lados_set': self.auto_troca_lados_set,
            'status': self.status,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None
        }


class ChaveamentoPartida(db.Model):
    __tablename__ = 'chaveamento_partidas'
    __table_args__ = (
        UniqueConstraint('campeonato_id', 'categoria', 'rodada', 'posicao', name='uq_chaveamento_partida_posicao'),
    )

    id = db.Column(db.Integer, primary_key=True)
    campeonato_id = db.Column(db.Integer, db.ForeignKey('campeonatos.id'), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    rodada = db.Column(db.Integer, nullable=False)
    posicao = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pendente')

    mesa_id = db.Column(db.Integer, db.ForeignKey('mesas.id'), nullable=True)
    jogador_1_inscrito_id = db.Column(db.Integer, db.ForeignKey('jogadores_inscritos.id'), nullable=True)
    jogador_2_inscrito_id = db.Column(db.Integer, db.ForeignKey('jogadores_inscritos.id'), nullable=True)
    vencedor_inscrito_id = db.Column(db.Integer, db.ForeignKey('jogadores_inscritos.id'), nullable=True)

    placar_sets_time1 = db.Column(db.Integer, nullable=True)
    placar_sets_time2 = db.Column(db.Integer, nullable=True)

    proxima_partida_id = db.Column(db.Integer, db.ForeignKey('chaveamento_partidas.id'), nullable=True)
    proximo_slot = db.Column(db.Integer, nullable=True)

    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mesa = db.relationship('Mesa', backref='partidas_chaveamento', lazy=True)
    jogador_1 = db.relationship('JogadorInscrito', foreign_keys=[jogador_1_inscrito_id], lazy=True)
    jogador_2 = db.relationship('JogadorInscrito', foreign_keys=[jogador_2_inscrito_id], lazy=True)
    vencedor = db.relationship('JogadorInscrito', foreign_keys=[vencedor_inscrito_id], lazy=True)
    proxima_partida = db.relationship('ChaveamentoPartida', remote_side=[id], backref='partidas_anteriores', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'campeonato_id': self.campeonato_id,
            'categoria': self.categoria,
            'rodada': self.rodada,
            'posicao': self.posicao,
            'status': self.status,
            'mesa_id': self.mesa_id,
            'jogador_1_inscrito_id': self.jogador_1_inscrito_id,
            'jogador_2_inscrito_id': self.jogador_2_inscrito_id,
            'vencedor_inscrito_id': self.vencedor_inscrito_id,
            'placar_sets_time1': self.placar_sets_time1,
            'placar_sets_time2': self.placar_sets_time2,
            'proxima_partida_id': self.proxima_partida_id,
            'proximo_slot': self.proximo_slot,
            'data_criacao': self.data_criacao.isoformat() if self.data_criacao else None,
            'data_atualizacao': self.data_atualizacao.isoformat() if self.data_atualizacao else None
        }


class GrupoChaveamento(db.Model):
    __tablename__ = 'grupos_chaveamento'
    __table_args__ = (UniqueConstraint('campeonato_id', 'categoria', 'numero', name='uq_grupo_campeonato_num'),)

    id = db.Column(db.Integer, primary_key=True)
    campeonato_id = db.Column(db.Integer, db.ForeignKey('campeonatos.id'), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    numero = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pendente')  # pendente, em_andamento, finalizado
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    partidas = db.relationship('PartidaGrupo', backref='grupo', lazy=True, cascade='all, delete-orphan')
    classificacoes = db.relationship('ClassificacaoGrupo', backref='grupo', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'campeonato_id': self.campeonato_id,
            'categoria': self.categoria,
            'numero': self.numero,
            'status': self.status
        }


class PartidaGrupo(db.Model):
    __tablename__ = 'partidas_grupo'

    id = db.Column(db.Integer, primary_key=True)
    campeonato_id = db.Column(db.Integer, db.ForeignKey('campeonatos.id'), nullable=False)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos_chaveamento.id'), nullable=False)
    categoria = db.Column(db.String(50), nullable=False)
    rodada_grupo = db.Column(db.Integer, nullable=False)
    posicao = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pronta')  # pronta, em_andamento, finalizada

    mesa_id = db.Column(db.Integer, db.ForeignKey('mesas.id'), nullable=True)
    jogador_1_inscrito_id = db.Column(db.Integer, db.ForeignKey('jogadores_inscritos.id'), nullable=True)
    jogador_2_inscrito_id = db.Column(db.Integer, db.ForeignKey('jogadores_inscritos.id'), nullable=True)
    vencedor_inscrito_id = db.Column(db.Integer, db.ForeignKey('jogadores_inscritos.id'), nullable=True)
    placar_sets_time1 = db.Column(db.Integer, nullable=True)
    placar_sets_time2 = db.Column(db.Integer, nullable=True)

    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    data_atualizacao = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    mesa = db.relationship('Mesa', backref='partidas_grupo', lazy=True)
    jogador_1 = db.relationship('JogadorInscrito', foreign_keys=[jogador_1_inscrito_id], lazy=True)
    jogador_2 = db.relationship('JogadorInscrito', foreign_keys=[jogador_2_inscrito_id], lazy=True)
    vencedor = db.relationship('JogadorInscrito', foreign_keys=[vencedor_inscrito_id], lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'campeonato_id': self.campeonato_id,
            'grupo_id': self.grupo_id,
            'categoria': self.categoria,
            'rodada_grupo': self.rodada_grupo,
            'posicao': self.posicao,
            'status': self.status,
            'mesa_id': self.mesa_id,
            'jogador_1_inscrito_id': self.jogador_1_inscrito_id,
            'jogador_2_inscrito_id': self.jogador_2_inscrito_id,
            'vencedor_inscrito_id': self.vencedor_inscrito_id,
            'placar_sets_time1': self.placar_sets_time1,
            'placar_sets_time2': self.placar_sets_time2
        }


class ClassificacaoGrupo(db.Model):
    __tablename__ = 'classificacoes_grupo'
    __table_args__ = (UniqueConstraint('grupo_id', 'jogador_inscrito_id', name='uq_classificacao_jogador'),)

    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey('grupos_chaveamento.id'), nullable=False)
    jogador_inscrito_id = db.Column(db.Integer, db.ForeignKey('jogadores_inscritos.id'), nullable=False)

    pontos = db.Column(db.Integer, default=0)
    partidas_vencidas = db.Column(db.Integer, default=0)
    partidas_perdidas = db.Column(db.Integer, default=0)
    sets_vencidos = db.Column(db.Integer, default=0)
    sets_perdidos = db.Column(db.Integer, default=0)
    posicao_final = db.Column(db.Integer, nullable=True)
    avancou = db.Column(db.Boolean, default=False)

    jogador = db.relationship('JogadorInscrito', foreign_keys=[jogador_inscrito_id], lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'grupo_id': self.grupo_id,
            'jogador_inscrito_id': self.jogador_inscrito_id,
            'pontos': self.pontos,
            'partidas_vencidas': self.partidas_vencidas,
            'partidas_perdidas': self.partidas_perdidas,
            'sets_vencidos': self.sets_vencidos,
            'sets_perdidos': self.sets_perdidos,
            'posicao_final': self.posicao_final,
            'avancou': self.avancou
        }
