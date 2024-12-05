from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    imagen = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<Producto {self.nombre}>'

class Venta(db.Model):
    __tablename__ = 'ventas'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)

    producto = db.relationship('Producto', backref='ventas')

    def __repr__(self):
        return f'<Venta {self.id} - {self.producto.nombre} - {self.total}>'
