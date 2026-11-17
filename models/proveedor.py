from models import db


class Proveedor(db.Model):
    __tablename__ = "proveedor"

    id_proveedor = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    cuit = db.Column(db.String(13), unique=True, nullable=False)
    telefono = db.Column(db.String(30))
    email = db.Column(db.String(120))
    activo = db.Column(db.Boolean, nullable=False, default=True)