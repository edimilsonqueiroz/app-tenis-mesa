from flask import Blueprint

def register_blueprints(app):
    from . import campeonatos, mesas, jogadores, placar, ranking
    
    app.register_blueprint(campeonatos.bp)
    app.register_blueprint(mesas.bp)
    app.register_blueprint(jogadores.bp)
    app.register_blueprint(placar.bp)
    app.register_blueprint(ranking.bp)
