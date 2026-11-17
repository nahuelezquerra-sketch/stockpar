from datetime import datetime, timezone

from models import db


class CotizacionDolar(db.Model):
    __tablename__ = "cotizacion_dolar"

    id_cotizacion_dolar = db.Column(db.Integer, primary_key=True)
    valor = db.Column(db.Numeric(12, 2), nullable=False)
    fuente = db.Column(db.String(100), nullable=False)
    fecha = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )

    __table_args__ = (
        db.CheckConstraint("valor > 0", name="ck_dolar_positivo"),
    )