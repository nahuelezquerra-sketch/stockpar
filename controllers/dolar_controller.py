import secrets
from decimal import Decimal, InvalidOperation

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from models import db
from models.cotizacion_dolar import CotizacionDolar

dolar_bp = Blueprint("dolar", __name__)


@dolar_bp.route("/dolar", methods=["GET", "POST"])
def listar():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    if request.method == "POST":
        token = request.form.get("csrf_token", "")

        if not secrets.compare_digest(token, session["csrf_token"]):
            return "Formulario vencido. Recargá la página.", 400

        try:
            valor = Decimal(request.form.get("valor", ""))
            fuente = request.form.get("fuente", "").strip()

            if not valor.is_finite():
                raise ValueError("Ingresá un valor válido.")

            if valor <= 0 or valor > Decimal("9999999999.99"):
                raise ValueError("El valor debe ser mayor que cero y no superar 9999999999.99.")

            if valor != valor.quantize(Decimal("0.01")):
                raise ValueError("El valor admite hasta dos decimales.")

            if not fuente or len(fuente) > 100:
                raise ValueError("Ingresá una fuente de hasta 100 caracteres.")

        except (ValueError, InvalidOperation) as error:
            flash(
                str(error)
                if isinstance(error, ValueError)
                else "Ingresá un valor numérico válido."
            )
        else:
            cotizacion = CotizacionDolar(
                valor=valor,
                fuente=fuente,
            )

            db.session.add(cotizacion)
            db.session.commit()

            flash("Cotización del dólar guardada correctamente.")
            return redirect(url_for("dolar.listar"))

    historial = CotizacionDolar.query.order_by(
        CotizacionDolar.fecha.desc(),
        CotizacionDolar.id_cotizacion_dolar.desc(),
    ).all()

    return render_template(
        "dolar.html",
        historial=historial,
        vigente=historial[0] if historial else None,
    )