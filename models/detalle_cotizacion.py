from models import db


class DetalleCotizacion(db.Model):
    __tablename__ = "detalle_cotizacion"

    id_detalle = db.Column(db.Integer, primary_key=True)

    id_cotizacion = db.Column(
        db.Integer,
        db.ForeignKey("cotizacion.id_cotizacion"),
        nullable=False,
    )

    id_repuesto = db.Column(
        db.Integer,
        db.ForeignKey("repuesto.id_repuesto"),
        nullable=False,
    )

    codigo_repuesto = db.Column(db.String(40), nullable=False)
    nombre_repuesto = db.Column(db.String(120), nullable=False)

    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(20, 2), nullable=False)
    subtotal = db.Column(db.Numeric(20, 2), nullable=False)

    cotizacion = db.relationship(
        "Cotizacion",
        back_populates="detalles",
    )

    repuesto = db.relationship("Repuesto")

    __table_args__ = (
        db.CheckConstraint(
            "cantidad > 0",
            name="ck_detalle_cantidad",
        ),
        db.CheckConstraint(
            "precio_unitario >= 0",
            name="ck_detalle_precio",
        ),
        db.CheckConstraint(
            "subtotal >= 0",
            name="ck_detalle_subtotal",
        ),
        db.UniqueConstraint(
            "id_cotizacion",
            "id_repuesto",
            name="uq_detalle_cotizacion_repuesto",
        ),
    )