import secrets
from decimal import Decimal

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError

from models import db
from models.repuesto import Repuesto
from models.cotizacion_dolar import CotizacionDolar
from models.cotizacion import Cotizacion
from models.detalle_cotizacion import DetalleCotizacion

cotizacion_bp = Blueprint("cotizacion", __name__)


@cotizacion_bp.route("/cotizaciones", methods=["GET", "POST"])
@login_required
def listar():
    if current_user.rol not in {"ADMINISTRADOR", "VENDEDOR"}:
        abort(403)

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    repuestos = Repuesto.query.filter_by(activo=True).order_by(
        Repuesto.nombre
    ).all()

    dolar = CotizacionDolar.query.order_by(
        CotizacionDolar.fecha.desc(),
        CotizacionDolar.id_cotizacion_dolar.desc(),
    ).first()

    if request.method == "POST":
        token = request.form.get("csrf_token", "")

        if not secrets.compare_digest(token, session["csrf_token"]):
            return "Formulario vencido. Recargá la página.", 400

        try:
            cliente = request.form.get("cliente_nombre", "").strip()
            contacto = request.form.get("cliente_contacto", "").strip()

            if not cliente or len(cliente) > 120:
                raise ValueError(
                    "Ingresá un cliente de hasta 120 caracteres."
                )

            if len(contacto) > 120:
                raise ValueError(
                    "El contacto admite hasta 120 caracteres."
                )

            if dolar is None:
                raise ValueError(
                    "Primero registrá una cotización del dólar."
                )

            cotizacion = Cotizacion(
                cliente_nombre=cliente,
                cliente_contacto=contacto,
                id_usuario=current_user.id_usuario,
                id_cotizacion_dolar=dolar.id_cotizacion_dolar,
                valor_dolar=dolar.valor,
                total=Decimal("0.00"),
                estado="BORRADOR",
            )

            for repuesto in repuestos:
                campo = f"cantidad_{repuesto.id_repuesto}"
                texto = request.form.get(campo, "0").strip()

                try:
                    cantidad = int(texto or "0")
                except ValueError:
                    raise ValueError(
                        f"La cantidad de {repuesto.codigo} debe ser entera."
                    )

                if cantidad < 0 or cantidad > 1000000:
                    raise ValueError(
                        "Las cantidades deben estar entre 0 y 1000000."
                    )

                if cantidad == 0:
                    continue

                precio = repuesto.calcular_precio_venta(dolar.valor)
                subtotal = precio * cantidad

                if subtotal > Decimal("999999999999999999.99"):
                    raise ValueError(
                        "El importe supera el máximo permitido."
                    )

                detalle = DetalleCotizacion(
                    id_repuesto=repuesto.id_repuesto,
                    codigo_repuesto=repuesto.codigo,
                    nombre_repuesto=repuesto.nombre,
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=subtotal,
                )

                cotizacion.detalles.append(detalle)
                cotizacion.total += subtotal

            if not cotizacion.detalles:
                raise ValueError(
                    "Ingresá una cantidad en al menos un repuesto."
                )

            if cotizacion.total > Decimal("999999999999999999.99"):
                raise ValueError(
                    "El total supera el máximo permitido."
                )

            db.session.add(cotizacion)
            db.session.commit()

        except ValueError as error:
            db.session.rollback()
            flash(str(error))

        except SQLAlchemyError:
            db.session.rollback()
            flash(
                "No se pudo guardar el presupuesto. Intentá nuevamente."
            )

        else:
            flash("Presupuesto guardado correctamente.")
            return redirect(
                url_for(
                    "cotizacion.ver",
                    id_cotizacion=cotizacion.id_cotizacion,
                )
            )

    historial = Cotizacion.query.order_by(
        Cotizacion.id_cotizacion.desc()
    ).all()

    return render_template(
        "cotizaciones.html",
        repuestos=repuestos,
        dolar=dolar,
        historial=historial,
    )


@cotizacion_bp.route("/cotizaciones/<int:id_cotizacion>")
@login_required
def ver(id_cotizacion):
    if current_user.rol not in {"ADMINISTRADOR", "VENDEDOR"}:
        abort(403)

    cotizacion = db.get_or_404(Cotizacion, id_cotizacion)

    return render_template(
        "cotizacion_detalle.html",
        cotizacion=cotizacion,
    )


@cotizacion_bp.route(
    "/cotizaciones/<int:id_cotizacion>/confirmar",
    methods=["POST"],
)
@login_required
def confirmar(id_cotizacion):
    if current_user.rol not in {"ADMINISTRADOR", "VENDEDOR"}:
        abort(403)

    token = request.form.get("csrf_token", "")
    esperado = session.get("csrf_token", "")

    if not token or not secrets.compare_digest(token, esperado):
        return "Formulario vencido. Recargá la página.", 400

    try:
        resultado = db.session.execute(
            update(Cotizacion)
            .where(
                Cotizacion.id_cotizacion == id_cotizacion,
                Cotizacion.estado == "BORRADOR",
            )
            .values(estado="CONFIRMADA")
            .execution_options(synchronize_session=False)
        )

        if resultado.rowcount != 1:
            raise ValueError(
                "El presupuesto no existe o ya no está en borrador."
            )

        detalles = DetalleCotizacion.query.filter_by(
            id_cotizacion=id_cotizacion
        ).order_by(DetalleCotizacion.id_repuesto).all()

        if not detalles:
            raise ValueError("El presupuesto no tiene repuestos.")

        for detalle in detalles:
            resultado_stock = db.session.execute(
                update(Repuesto)
                .where(
                    Repuesto.id_repuesto == detalle.id_repuesto,
                    Repuesto.activo.is_(True),
                    Repuesto.stock_actual >= detalle.cantidad,
                )
                .values(
                    stock_actual=Repuesto.stock_actual - detalle.cantidad
                )
                .execution_options(synchronize_session=False)
            )

            if resultado_stock.rowcount != 1:
                raise ValueError(
                    f"No se puede vender {detalle.codigo_repuesto}: "
                    "stock insuficiente o repuesto inactivo."
                )

        db.session.commit()

    except ValueError as error:
        db.session.rollback()
        flash(str(error))

    except SQLAlchemyError:
        db.session.rollback()
        flash(
            "No se pudo confirmar la venta. Intentá nuevamente."
        )

    else:
        flash("Venta confirmada. El stock fue actualizado.")

    return redirect(
        url_for(
            "cotizacion.ver",
            id_cotizacion=id_cotizacion,
        )
)
@cotizacion_bp.route(
    "/cotizaciones/<int:id_cotizacion>/cancelar",
    methods=["POST"],
)
@login_required
def cancelar(id_cotizacion):
    if current_user.rol not in {"ADMINISTRADOR", "VENDEDOR"}:
        abort(403)

    token = request.form.get("csrf_token", "")
    esperado = session.get("csrf_token", "")

    if not token or not secrets.compare_digest(token, esperado):
        return "Formulario vencido. Recargá la página.", 400

    try:
        resultado = db.session.execute(
            update(Cotizacion)
            .where(
                Cotizacion.id_cotizacion == id_cotizacion,
                Cotizacion.estado == "BORRADOR",
            )
            .values(estado="CANCELADA")
            .execution_options(synchronize_session=False)
        )

        if resultado.rowcount != 1:
            raise ValueError(
                "El presupuesto no existe o ya no está en borrador."
            )

        db.session.commit()

    except ValueError as error:
        db.session.rollback()
        flash(str(error))

    except SQLAlchemyError:
        db.session.rollback()
        flash("No se pudo cancelar el presupuesto.")

    else:
        flash("Presupuesto cancelado. El stock no fue modificado.")

    return redirect(
        url_for("cotizacion.ver", id_cotizacion=id_cotizacion)
    )