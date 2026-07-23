from flask import Flask
from flask_bootstrap import Bootstrap

bootstrap=Bootstrap()

def create_app():
	app=Flask(__name__)
	bootstrap.init_app(app)

	from app.main import bp as main_bp
	app.register_blueprint(main_bp,
					   url_prefix='/',
					   static_folder='static',
					   static_url_path='static')
	return app
# from app import routes