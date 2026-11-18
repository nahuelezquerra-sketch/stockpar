from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import or_
from models import db
from models.cotizacion import Cotizacion

from models.repuesto import Repuesto
from models.cotizacion_dolar import CotizacionDolar
from flask import current_app, g
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from decimal import Decimal
from sqlalchemy.exc import SQLAlchemyError
from models.detalle_cotizacion import DetalleCotizacion
from sqlalchemy import update
from flask import abort
from flask_login import current_user, login_required
from sqlalchemy import update

from models.usuario import Usuario

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


def error_api(codigo, mensaje, estado):
    return jsonify({
        "code": codigo,
        "message": mensaje,
        "details": {},
    }), estado


@api_bp.before_request
def verificar_acceso():
    if request.endpoint == "api.obtener_token":
        return None

    autorizacion = request.headers.get("Authorization", "")
    usuario = None

    if autorizacion:
        partes = autorizacion.split()

        if len(partes) != 2 or partes[0].lower() != "bearer":
            return error_api(
                "TOKEN_INVALIDO",
                "Usá Authorization: Bearer seguido del token.",
                401,
            )

        serializador = URLSafeTimedSerializer(
            current_app.config["SECRET_KEY"],
            salt="stockpar-api",
        )

        try:
            datos = serializador.loads(partes[1], max_age=3600)
            id_usuario = int(datos["id_usuario"])
        except SignatureExpired:
            return error_api(
                "TOKEN_VENCIDO",
                "El token venció. Solicitá uno nuevo.",
                401,
            )
        except (BadSignature, KeyError, TypeError, ValueError):
            return error_api(
                "TOKEN_INVALIDO",
                "El token no es válido.",
                401,
            )

        usuario = db.session.get(Usuario, id_usuario)

    elif current_user.is_authenticated:
        usuario = current_user

    if usuario is None or not usuario.activo:
        return error_api(
            "NO_AUTENTICADO",
            "Iniciá sesión o enviá un token válido.",
            401,
        )

    if usuario.rol not in {"ADMINISTRADOR", "VENDEDOR"}:
        return error_api(
            "SIN_PERMISO",
            "No tenés permiso para consultar la API.",
            403,
        )

    g.usuario_api = usuario


@api_bp.route("/repuestos", methods=["GET"])
def listar_repuestos():
    busqueda = request.args.get("q", "").strip()

    consulta = Repuesto.query.filter_by(activo=True)

    if busqueda:
        consulta = consulta.filter(
            or_(
                Repuesto.codigo.contains(busqueda, autoescape=True),
                Repuesto.nombre.contains(busqueda, autoescape=True),
                Repuesto.marca.contains(busqueda, autoescape=True),
            )
        )

    repuestos = consulta.order_by(Repuesto.nombre).all()
    dolar = obtener_dolar_vigente()

    datos = []

    for repuesto in repuestos:
        precio = (
            str(repuesto.calcular_precio_venta(dolar.valor))
            if dolar
            else None
        )

        datos.append({
            "id_repuesto": repuesto.id_repuesto,
            "codigo": repuesto.codigo,
            "nombre": repuesto.nombre,
            "marca": repuesto.marca,
            "stock_actual": repuesto.stock_actual,
            "stock_minimo": repuesto.stock_minimo,
            "bajo_stock": repuesto.requiere_reposicion(),
            "precio_venta_ars": precio,
        })

    return jsonify({
        "cantidad": len(datos),
        "dolar_utilizado": str(dolar.valor) if dolar else None,
        "repuestos": datos,
    })


@api_bp.route("/cotizaciones-dolar/vigente", methods=["GET"])
def consultar_dolar():
    dolar = obtener_dolar_vigente()

    if dolar is None:
        return error_api(
            "DOLAR_NO_REGISTRADO",
            "Todavía no hay una cotización del dólar.",
            404,
        )

    return jsonify({
        "id_cotizacion_dolar": dolar.id_cotizacion_dolar,
        "valor": str(dolar.valor),
        "fuente": dolar.fuente,
        "fecha": dolar.fecha.isoformat() + "Z",
    })
@api_bp.route("/cotizaciones/<int:id_cotizacion>", methods=["GET"])
def consultar_presupuesto(id_cotizacion):
    cotizacion = db.session.get(Cotizacion, id_cotizacion)

    if cotizacion is None:
        return error_api(
            "PRESUPUESTO_NO_ENCONTRADO",
            "El presupuesto solicitado no existe.",
            404,
        )

    items = []

    for detalle in cotizacion.detalles:
        items.append({
            "id_repuesto": detalle.id_repuesto,
            "codigo": detalle.codigo_repuesto,
            "nombre": detalle.nombre_repuesto,
            "cantidad": detalle.cantidad,
            "precio_unitario": str(detalle.precio_unitario),
            "subtotal": str(detalle.subtotal),
        })

    return jsonify({
        "id": cotizacion.id_cotizacion,
        "cliente_nombre": cotizacion.cliente_nombre,
        "cliente_contacto": cotizacion.cliente_contacto,
        "id_usuario": cotizacion.id_usuario,
        "fecha": cotizacion.fecha.isoformat() + "Z",
        "estado": cotizacion.estado,
        "cotizacion_dolar": str(cotizacion.valor_dolar),
        "total": str(cotizacion.total),
        "items": items,
    })
@api_bp.route("/auth/login", methods=["POST"])
def obtener_token():
    if not request.is_json:
        return error_api(
            "FORMATO_INVALIDO",
            "Enviá los datos en formato JSON.",
            415,
        )

    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return error_api(
            "DATOS_INVALIDOS",
            "Se esperaba un objeto JSON.",
            400,
        )

    email = datos.get("email", "")
    password = datos.get("password", "")

    if not isinstance(email, str) or not isinstance(password, str):
        return error_api(
            "DATOS_INVALIDOS",
            "Email y contraseña deben ser textos.",
            400,
        )

    usuario = Usuario.query.filter_by(
        email=email.strip().lower()
    ).first()

    if (
        usuario is None
        or not usuario.activo
        or not usuario.verificar_password(password)
    ):
        return error_api(
            "CREDENCIALES_INVALIDAS",
            "Email o contraseña incorrectos.",
            401,
        )

    serializador = URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt="stockpar-api",
    )

    token = serializador.dumps({
        "id_usuario": usuario.id_usuario,
    })

    return jsonify({
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "rol": usuario.rol,
    })
def obtener_dolar_vigente():
    return CotizacionDolar.query.order_by(
        CotizacionDolar.fecha.desc(),
        CotizacionDolar.id_cotizacion_dolar.desc(),
    ).first()
@api_bp.route("/cotizaciones", methods=["POST"])
def crear_presupuesto():
    # Esta operación requiere token, no solamente sesión del navegador.
    if not request.headers.get("Authorization"):
        return error_api(
            "TOKEN_REQUERIDO",
            "Enviá un token Bearer para crear presupuestos.",
            401,
        )

    if not request.is_json:
        return error_api(
            "FORMATO_INVALIDO",
            "Enviá los datos en formato JSON.",
            415,
        )

    datos = request.get_json(silent=True)

    if not isinstance(datos, dict):
        return error_api(
            "DATOS_INVALIDOS",
            "Se esperaba un objeto JSON.",
            400,
        )

    try:
        cliente = datos.get("cliente_nombre", "")
        contacto = datos.get("cliente_contacto", "")
        items = datos.get("items")

        if not isinstance(cliente, str) or not cliente.strip():
            raise ValueError("Ingresá el nombre del cliente.")

        if not isinstance(contacto, str):
            raise ValueError("El contacto debe ser un texto.")

        if len(cliente.strip()) > 120 or len(contacto.strip()) > 120:
            raise ValueError("Cliente y contacto admiten hasta 120 caracteres.")

        if not isinstance(items, list) or not items:
            raise ValueError("El presupuesto debe tener al menos un repuesto.")

        if len(items) > 100:
            raise ValueError("Se permiten hasta 100 repuestos por presupuesto.")

        dolar = obtener_dolar_vigente()

        if dolar is None:
            return error_api(
                "DOLAR_NO_REGISTRADO",
                "Primero registrá una cotización del dólar.",
                409,
            )

        cotizacion = Cotizacion(
            cliente_nombre=cliente.strip(),
            cliente_contacto=contacto.strip(),
            id_usuario=g.usuario_api.id_usuario,
            id_cotizacion_dolar=dolar.id_cotizacion_dolar,
            valor_dolar=dolar.valor,
            estado="BORRADOR",
            total=Decimal("0.00"),
        )

        incluidos = set()
        limite = Decimal("999999999999999999.99")

        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Cada item debe ser un objeto JSON.")

            id_repuesto = item.get("id_repuesto")
            cantidad = item.get("cantidad")

            if type(id_repuesto) is not int or id_repuesto <= 0:
                raise ValueError("El identificador del repuesto debe ser entero positivo.")

            if type(cantidad) is not int or not 1 <= cantidad <= 1000000:
                raise ValueError("La cantidad debe ser entera entre 1 y 1000000.")

            if id_repuesto in incluidos:
                raise ValueError("No repitas el mismo repuesto en varios items.")

            incluidos.add(id_repuesto)
            repuesto = db.session.get(Repuesto, id_repuesto)

            if repuesto is None or not repuesto.activo:
                raise ValueError(
                    f"El repuesto {id_repuesto} no existe o está inactivo."
                )

            precio = repuesto.calcular_precio_venta(dolar.valor)
            subtotal = precio * cantidad

            if subtotal > limite or cotizacion.total + subtotal > limite:
                raise ValueError("El total supera el máximo permitido.")

            cotizacion.detalles.append(
                DetalleCotizacion(
                    id_repuesto=repuesto.id_repuesto,
                    codigo_repuesto=repuesto.codigo,
                    nombre_repuesto=repuesto.nombre,
                    cantidad=cantidad,
                    precio_unitario=precio,
                    subtotal=subtotal,
                )
            )

            cotizacion.total += subtotal

        db.session.add(cotizacion)
        db.session.flush()

        respuesta = {
            "id": cotizacion.id_cotizacion,
            "estado": cotizacion.estado,
            "cliente_nombre": cotizacion.cliente_nombre,
            "cotizacion_dolar": str(cotizacion.valor_dolar),
            "total": str(cotizacion.total),
            "items": [
                {
                    "id_repuesto": detalle.id_repuesto,
                    "cantidad": detalle.cantidad,
                    "precio_unitario": str(detalle.precio_unitario),
                    "subtotal": str(detalle.subtotal),
                }
                for detalle in cotizacion.detalles
            ],
        }

        db.session.commit()

    except ValueError as error:
        db.session.rollback()
        return error_api("VALIDACION", str(error), 422)

    except SQLAlchemyError:
        db.session.rollback()
        return error_api(
            "ERROR_BASE_DATOS",
            "No se pudo guardar el presupuesto.",
            500,
        )

    return jsonify(respuesta), 201
@api_bp.route(
    "/cotizaciones/<int:id_cotizacion>/confirmar",
    methods=["POST"],
)
def confirmar_presupuesto_api(id_cotizacion):
    if not request.headers.get("Authorization"):
        return error_api(
            "TOKEN_REQUERIDO",
            "Enviá un token Bearer para confirmar ventas.",
            401,
        )

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
            db.session.rollback()

            cotizacion = db.session.get(Cotizacion, id_cotizacion)

            if cotizacion is None:
                return error_api(
                    "PRESUPUESTO_NO_ENCONTRADO",
                    "El presupuesto no existe.",
                    404,
                )

            return error_api(
                "ESTADO_INVALIDO",
                "Solo puede confirmarse un presupuesto en borrador.",
                409,
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
        return error_api("CONFLICTO_STOCK", str(error), 409)

    except SQLAlchemyError:
        db.session.rollback()
        return error_api(
            "ERROR_BASE_DATOS",
            "No se pudo confirmar la venta.",
            500,
        )

    return jsonify({
        "id": id_cotizacion,
        "estado": "CONFIRMADA",
        "message": "Venta confirmada. El stock fue actualizado.",
    })
