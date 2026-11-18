import secrets
from decimal import Decimal, InvalidOperation

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
from sqlalchemy import or_, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from models import db
from models.proveedor import Proveedor
from models.repuesto import Repuesto
from models.cotizacion_dolar import CotizacionDolar

repuesto_bp = Blueprint("repuesto", __name__)


@repuesto_bp.route("/repuestos", methods=["GET", "POST"])
@login_required
def listar():
    busqueda = request.args.get("q", "").strip()

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    if request.method == "POST":
        if current_user.rol != "ADMINISTRADOR":
            abort(403)

        token = request.form.get("csrf_token", "")

        if not token or not secrets.compare_digest(
            token, session["csrf_token"]
        ):
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
                raise ValueError(
                    "El costo y el margen no pueden ser negativos."
                )

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

            if not 0 <= stock <= 2147483647:
                raise ValueError("Ingresá un stock válido.")

            if not 0 <= minimo <= 2147483647:
                raise ValueError("Ingresá un stock mínimo válido.")

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
            flash(
                "No se pudo guardar. Comprobá que el código no esté repetido."
            )

        except SQLAlchemyError:
            db.session.rollback()
            flash("No se pudo guardar el repuesto.")

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


@repuesto_bp.route("/repuestos/reposicion", methods=["GET", "POST"])
@login_required
def reponer_stock():
    if current_user.rol != "ADMINISTRADOR":
        abort(403)

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    if request.method == "POST":
        token = request.form.get("csrf_token", "")

        if not token or not secrets.compare_digest(
            token, session["csrf_token"]
        ):
            return "Formulario vencido. Recargá la página.", 400

        try:
            id_repuesto = int(request.form.get("id_repuesto", ""))
            cantidad = int(request.form.get("cantidad", ""))

            if not 1 <= cantidad <= 1000000:
                raise ValueError(
                    "Ingresá una cantidad entre 1 y 1000000."
                )

            resultado = db.session.execute(
                update(Repuesto)
                .where(
                    Repuesto.id_repuesto == id_repuesto,
                    Repuesto.activo.is_(True),
                    Repuesto.stock_actual <= 2147483647 - cantidad,
                )
                .values(
                    stock_actual=Repuesto.stock_actual + cantidad
                )
                .execution_options(synchronize_session=False)
            )

            if resultado.rowcount != 1:
                raise ValueError(
                    "El repuesto no está disponible o supera el límite de stock."
                )

            db.session.commit()

        except ValueError as error:
            db.session.rollback()
            flash(str(error))

        except SQLAlchemyError:
            db.session.rollback()
            flash("No se pudo registrar la reposición.")

        else:
            flash("Reposición registrada correctamente.")
            return redirect(url_for("repuesto.reponer_stock"))

    repuestos = Repuesto.query.filter_by(activo=True).order_by(
        Repuesto.nombre
    ).all()

    return render_template(
        "reposicion.html",
        repuestos=repuestos,
    )
@repuesto_bp.route(
    "/repuestos/<int:id_repuesto>/editar",
    methods=["GET", "POST"],
)
@login_required
def editar(id_repuesto):
    if current_user.rol != "ADMINISTRADOR":
        abort(403)

    repuesto = db.get_or_404(Repuesto, id_repuesto)

    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)

    if request.method == "POST":
        token = request.form.get("csrf_token", "")

        if not token or not secrets.compare_digest(
            token, session["csrf_token"]
        ):
            return "Formulario vencido. Recargá la página.", 400

        try:
            nombre = request.form.get("nombre", "").strip()
            marca = request.form.get("marca", "").strip()

            if not nombre or len(nombre) > 120:
                raise ValueError("Ingresá un nombre de hasta 120 caracteres.")

            if not marca or len(marca) > 80:
                raise ValueError("Ingresá una marca de hasta 80 caracteres.")

            costo = Decimal(request.form.get("precio_compra_usd", ""))
            margen = Decimal(request.form.get("margen_ganancia", ""))

            if not costo.is_finite() or not margen.is_finite():
                raise ValueError("Ingresá importes válidos.")

            if not Decimal("0") <= costo <= Decimal("9999999999.99"):
                raise ValueError("El costo está fuera del rango permitido.")

            if not Decimal("0") <= margen <= Decimal("99999.99"):
                raise ValueError("El margen está fuera del rango permitido.")

            if costo != costo.quantize(Decimal("0.01")):
                raise ValueError("El costo admite hasta dos decimales.")

            if margen != margen.quantize(Decimal("0.01")):
                raise ValueError("El margen admite hasta dos decimales.")

            minimo = int(request.form.get("stock_minimo", ""))

            if not 0 <= minimo <= 2147483647:
                raise ValueError("Ingresá un stock mínimo válido.")

            repuesto.nombre = nombre
            repuesto.marca = marca
            repuesto.precio_compra_usd = costo
            repuesto.margen_ganancia = margen
            repuesto.stock_minimo = minimo

            db.session.commit()

        except (ValueError, InvalidOperation) as error:
            db.session.rollback()
            flash(
                str(error)
                if isinstance(error, ValueError)
                else "Ingresá valores numéricos válidos."
            )

        except SQLAlchemyError:
            db.session.rollback()
            flash("No se pudo actualizar el repuesto.")

        else:
            flash("Repuesto actualizado correctamente.")
            return redirect(url_for("repuesto.listar"))

    return render_template(
        "repuesto_editar.html",
        repuesto=repuesto,
    )