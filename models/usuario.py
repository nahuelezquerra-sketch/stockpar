from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from models import db


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuario"

    id_usuario = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default="VENDEDOR")
    activo = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        db.CheckConstraint(
            "rol IN ('ADMINISTRADOR', 'VENDEDOR')",
            name="ck_usuario_rol",
        ),
    )

    def get_id(self):
        return str(self.id_usuario)

    @property
    def is_active(self):
        return self.activo

    def establecer_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verificar_password(self, password):
        return check_password_hash(self.password_hash, password)