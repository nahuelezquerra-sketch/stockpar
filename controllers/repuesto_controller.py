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
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError

from models import db
from models.proveedor import Proveedor
from models.repuesto import Repuesto
from models.cotizacion_dolar import CotizacionDolar

repuesto_bp = Blueprint("repuesto", __name__)


@repuesto_bp.route("/repuestos", methods=["GET", "POST"])
def listar():
    busqueda = request.args.get("q", "").strip()

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    if request.method == "POST":
        token = request.form.get("csrf_token", "")

        if not secrets.compare_digest(token, session["csrf_token"]):
            return "Formulario vencido. Recargá la página.", 400

        try:
            codigo = request.form.get("codigo", "").strip()
            nombre = request.form.get("nombre", "").strip()
            marca = request.form.get("marca", "").strip()

            if not codigo or not nombre or not marca:
                raise ValueError("Completá código, nombre y marca.")

            if len(codigo) > 40 or len(nombre) > 120 or len(marca) > 80:
                raise ValueError("Código, nombre o marca demasiado largos.")

            costo = Decimal(request.form.get("precio_compra_usd", ""))
            margen = Decimal(request.form.get("margen_ganancia", ""))

            if not costo.is_finite() or not margen.is_finite():
                raise ValueError("Ingresá importes válidos.")

            if costo < 0 or margen < 0:
                raise ValueError("El costo y el margen no pueden ser negativos.")

            if costo > Decimal("9999999999.99"):
                raise ValueError("El costo supera el máximo permitido.")

            if margen > Decimal("99999.99"):
                raise ValueError("El margen supera el máximo permitido.")

            if costo != costo.quantize(Decimal("0.01")):
                raise ValueError("El costo admite hasta dos decimales.")

            if margen != margen.quantize(Decimal("0.01")):
                raise ValueError("El margen admite hasta dos decimales.")

            stock = int(request.form.get("stock_actual", ""))
            minimo = int(request.form.get("stock_minimo", ""))
            id_proveedor = int(request.form.get("id_proveedor", ""))

            if stock < 0 or minimo < 0:
                raise ValueError("El stock no puede ser negativo.")

            proveedor = db.session.get(Proveedor, id_proveedor)

            if proveedor is None or not proveedor.activo:
                raise ValueError("Elegí un proveedor activo.")

            repuesto = Repuesto(
                codigo=codigo,
                nombre=nombre,
                marca=marca,
                precio_compra_usd=costo,
                margen_ganancia=margen,
                stock_actual=stock,
                stock_minimo=minimo,
                id_proveedor=proveedor.id_proveedor,
            )

            db.session.add(repuesto)
            db.session.commit()

        except (ValueError, InvalidOperation) as error:
            db.session.rollback()
            flash(
                str(error)
                if isinstance(error, ValueError)
                else "Ingresá valores numéricos válidos."
            )

        except IntegrityError:
            db.session.rollback()
            flash("No se pudo guardar. Comprobá que el código no esté repetido.")

        else:
            flash("Repuesto guardado correctamente.")
            return redirect(url_for("repuesto.listar"))

    consulta = Repuesto.query

    if busqueda:
        consulta = consulta.filter(
            or_(
                Repuesto.codigo.contains(busqueda, autoescape=True),
                Repuesto.nombre.contains(busqueda, autoescape=True),
                Repuesto.marca.contains(busqueda, autoescape=True),
            )
        )

    repuestos = consulta.order_by(Repuesto.nombre).all()

    proveedores = Proveedor.query.filter_by(activo=True).order_by(
        Proveedor.nombre
    ).all()

    dolar_vigente = CotizacionDolar.query.order_by(
        CotizacionDolar.fecha.desc(),
        CotizacionDolar.id_cotizacion_dolar.desc(),
    ).first()

    return render_template(
        "repuestos.html",
        repuestos=repuestos,
        proveedores=proveedores,
        dolar_vigente=dolar_vigente,
    )