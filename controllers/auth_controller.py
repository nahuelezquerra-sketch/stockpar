import secrets

from flask import (
    Blueprint, flash, redirect, render_template,
    request, session, url_for,
)
from flask_login import (
    current_user, login_required, login_user, logout_user,
)

from models.usuario import Usuario

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("inicio"))

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    if request.method == "POST":
        token = request.form.get("csrf_token", "")

        if not secrets.compare_digest(token, session["csrf_token"]):
            return "Formulario vencido. Recargá la página.", 400

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        usuario = Usuario.query.filter_by(email=email).first()

        if (
            usuario is not None
            and usuario.activo
            and usuario.verificar_password(password)
        ):
            session.clear()
            login_user(usuario)
            session["csrf_token"] = secrets.token_hex(32)
            return redirect(url_for("inicio"))

        flash("Email o contraseña incorrectos.")

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    token = request.form.get("csrf_token", "")

    if not secrets.compare_digest(token, session.get("csrf_token", "")) or not token:
        return "Formulario vencido. Recargá la página.", 400

    logout_user()
    session.clear()
    return redirect(url_for("auth.login"))