from flask import Flask

def create_app():
    app = Flask(__name__)

    app.secret_key = "qualquer_coisa_segura"

    from app.routes import auth_routes
    from app.routes import conta_routes  

    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(conta_routes.bp) 

    return app