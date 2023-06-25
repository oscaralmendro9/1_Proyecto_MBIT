from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)

    # Configuracion de la BBDD, utilizando MySQL (La contraseña de la BBDD podria ir por env)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mbit:mbit@localhost/mydatabase'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)

    from .models import Picture, Tag
    
    from . import views
    app.register_blueprint(views.bp)

    # Crear la base de datos si no existe (Si existe no la creará)
    with app.app_context():
        db.create_all()

    return app