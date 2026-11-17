from datetime import datetime, timezone

from models import db


class Cotizacion(db.Model):
    __tablename__ = "cotizacion"

    id_cotizacion = db.Column(db.Integer, primary_key=True)

    cliente_nombre = db.Column(db.String(120), nullable=False)
    cliente_contacto = db.Column(db.String(120))

    fecha = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    estado = db.Column(
        db.String(20),
        nullable=False,
        default="BORRADOR",
    )

    total = db.Column(db.Numeric(20, 2), nullable=False)

    id_usuario = db.Column(
        db.Integer,
        db.ForeignKey("usuario.id_usuario"),
        nullable=False,
    )

    id_cotizacion_dolar = db.Column(
        db.Integer,
        db.ForeignKey("cotizacion_dolar.id_cotizacion_dolar"),
        nullable=False,
    )

    valor_dolar = db.Column(db.Numeric(12, 2), nullable=False)

    usuario = db.relationship("Usuario")
    cotizacion_dolar = db.relationship("CotizacionDolar")

    detalles = db.relationship(
        "DetalleCotizacion",
        back_populates="cotizacion",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        db.CheckConstraint(
            "estado IN ('BORRADOR', 'CONFIRMADA', 'CANCELADA')",
            name="ck_cotizacion_estado",
        ),
        db.CheckConstraint(
            "total >= 0",
            name="ck_cotizacion_total",
        ),
        db.CheckConstraint(
            "valor_dolar > 0",
            name="ck_cotizacion_dolar",
        ),
    )