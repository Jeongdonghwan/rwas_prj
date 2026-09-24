from pathlib import Path

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    Path(app.root_path).parent.joinpath("instance").mkdir(exist_ok=True)

    db.init_app(app)

    from app.config import LAWYER, SITE_DEFAULTS

    import os
    _static = Path(app.static_folder)
    try:
        asset_ver = str(int(max(
            os.path.getmtime(_static / "css" / "site.css"),
            os.path.getmtime(_static / "js" / "site.js"),
        )))
    except OSError:
        asset_ver = "1"

    @app.context_processor
    def inject_site():
        return {"site": SITE_DEFAULTS, "lawyer": LAWYER, "asset_ver": asset_ver}

    from app.routes.main import bp as main_bp
    from app.routes.contact import bp as contact_bp
    from app.routes.admin import bp as admin_bp
    from app.routes.area import bp as area_bp
    from app.routes.job import bp as job_bp
    from app.routes.ko import bp as ko_bp
    from app.routes.board import bp as board_bp
    from app.routes.seo import bp as seo_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(area_bp)
    app.register_blueprint(job_bp)
    app.register_blueprint(ko_bp)
    app.register_blueprint(board_bp)
    app.register_blueprint(seo_bp)

    from app.seed import seed_command

    app.cli.add_command(seed_command)

    with app.app_context():
        from app import models  # noqa: F401

        db.create_all()

    return app
