import secrets

import click
from flask import Flask, render_template
from flask_login import LoginManager, current_user, login_required

from models import db
from models.proveedor import Proveedor
from models.repuesto import Repuesto
from models.cotizacion_dolar import CotizacionDolar
from models.usuario import Usuario

from controllers.proveedor_controller import proveedor_bp
from controllers.repuesto_controller import repuesto_bp
from controllers.dolar_controller import dolar_bp
from controllers.auth_controller import auth_bp
from models.cotizacion import Cotizacion
from models.detalle_cotizacion import DetalleCotizacion
from controllers.cotizacion_controller import cotizacion_bp
from controllers.api_controller import api_bp
from pathlib import Path

app = Flask(__name__)

carpeta_instance = Path(app.instance_path)
carpeta_instance.mkdir(parents=True, exist_ok=True)

archivo_clave = carpeta_instance / "secret_key.txt"

if not archivo_clave.exists():
    archivo_clave.write_text(secrets.token_hex(32), encoding="utf-8")

app.config["SECRET_KEY"] = archivo_clave.read_text(
    encoding="utf-8"
).strip()
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///stockpar.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login"
login_manager.login_message = "Iniciá sesión para continuar."


@login_manager.user_loader
def cargar_usuario(id_usuario):
    try:
        usuario = db.session.get(Usuario, int(id_usuario))
    except (ValueError, TypeError):
        return None

    return usuario if usuario and usuario.activo else None


app.register_blueprint(proveedor_bp)
app.register_blueprint(repuesto_bp)
app.register_blueprint(dolar_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(cotizacion_bp)
app.register_blueprint(api_bp)


with app.app_context():
    db.create_all()


@app.before_request
def proteger_pantallas():
    from flask import abort, request

    protegidos = {"proveedor", "repuesto", "dolar"}

    if request.blueprint not in protegidos:
        return None

    if not current_user.is_authenticated:
        return login_manager.unauthorized()

    if current_user.rol == "ADMINISTRADOR":
        return None

    # El vendedor no puede acceder a la gestión de proveedores.
    if request.blueprint == "proveedor":
        abort(403)

    # Puede consultar repuestos y dólar, pero no modificarlos.
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        abort(403)


@app.route("/")
@login_required
def inicio():
    return render_template("inicio.html")


@app.cli.command("crear-usuario")
@click.option("--nombre", prompt="Nombre")
@click.option("--email", prompt="Email")
@click.option(
    "--rol",
    type=click.Choice(["ADMINISTRADOR", "VENDEDOR"]),
    prompt="Rol",
)
@click.password_option()
def crear_usuario(nombre, email, rol, password):
    nombre = nombre.strip()
    email = email.strip().lower()

    if not nombre or len(nombre) > 120:
        raise click.ClickException("Ingresá un nombre de hasta 120 caracteres.")

    if not email or "@" not in email or len(email) > 120:
        raise click.ClickException("Ingresá un email válido.")

    if len(password) < 8:
        raise click.ClickException("La contraseña debe tener al menos 8 caracteres.")

    if Usuario.query.filter_by(email=email).first():
        raise click.ClickException("Ese email ya está registrado.")

    usuario = Usuario(nombre=nombre, email=email, rol=rol)
    usuario.establecer_password(password)

    db.session.add(usuario)
    db.session.commit()

    click.echo("Usuario creado correctamente.")


if __name__ == "__main__":
    app.run(debug=True, port=5050)