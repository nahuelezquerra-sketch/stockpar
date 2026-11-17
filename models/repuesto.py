from decimal import Decimal, ROUND_HALF_UP

from models import db


class Repuesto(db.Model):
    __tablename__ = "repuesto"

    id_repuesto = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(40), unique=True, nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    marca = db.Column(db.String(80), nullable=False)

    precio_compra_usd = db.Column(db.Numeric(12, 2), nullable=False)
    margen_ganancia = db.Column(db.Numeric(7, 2), nullable=False)

    stock_actual = db.Column(db.Integer, nullable=False, default=0)
    stock_minimo = db.Column(db.Integer, nullable=False, default=0)
    activo = db.Column(db.Boolean, nullable=False, default=True)

    id_proveedor = db.Column(
        db.Integer,
        db.ForeignKey("proveedor.id_proveedor"),
        nullable=False,
    )

    proveedor = db.relationship(
        "Proveedor",
        backref="repuestos",
    )

    __table_args__ = (
        db.CheckConstraint(
            "precio_compra_usd >= 0",
            name="ck_repuesto_costo",
        ),
        db.CheckConstraint(
            "margen_ganancia >= 0",
            name="ck_repuesto_margen",
        ),
        db.CheckConstraint(
            "stock_actual >= 0",
            name="ck_repuesto_stock",
        ),
        db.CheckConstraint(
            "stock_minimo >= 0",
            name="ck_repuesto_minimo",
        ),
    )

    def calcular_precio_venta(self, cotizacion_dolar):
        dolar = Decimal(str(cotizacion_dolar))

        if not dolar.is_finite() or dolar <= 0:
            raise ValueError("La cotización debe ser mayor que cero.")

        precio = (
            self.precio_compra_usd
            * dolar
            * (Decimal("1") + self.margen_ganancia / Decimal("100"))
        )

        return precio.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    def requiere_reposicion(self):
        return self.stock_actual <= self.stock_minimo