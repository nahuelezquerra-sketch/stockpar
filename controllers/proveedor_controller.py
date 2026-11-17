import secrets

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from sqlalchemy.exc import IntegrityError

from models import db
from models.proveedor import Proveedor

proveedor_bp = Blueprint("proveedor", __name__)


@proveedor_bp.route("/proveedores", methods=["GET", "POST"])
def listar():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    if request.method == "POST":
        token = request.form.get("csrf_token", "")

        if not secrets.compare_digest(token, session["csrf_token"]):
            return "Formulario vencido. Recargá la página.", 400

        nombre = request.form.get("nombre", "").strip()
        cuit = request.form.get("cuit", "").strip().replace("-", "")
        telefono = request.form.get("telefono", "").strip()
        email = request.form.get("email", "").strip()

        if not nombre or len(nombre) > 120:
            flash("Ingresá un nombre de hasta 120 caracteres.")
        elif not cuit.isascii() or not cuit.isdigit() or len(cuit) != 11:
            flash("El CUIT debe tener 11 números.")
        elif len(telefono) > 30 or len(email) > 120:
            flash("El teléfono o el email son demasiado largos.")
        elif email and ("@" not in email or "." not in email.split("@")[-1]):
            flash("Ingresá un email válido.")
        else:
            proveedor = Proveedor(
                nombre=nombre,
                cuit=cuit,
                telefono=telefono,
                email=email,
            )

            try:
                db.session.add(proveedor)
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Ya existe un proveedor con ese CUIT.")
            else:
                flash("Proveedor guardado correctamente.")
                return redirect(url_for("proveedor.listar"))

    proveedores = Proveedor.query.order_by(Proveedor.nombre).all()

    return render_template(
        "proveedores.html",
        proveedores=proveedores,
    )