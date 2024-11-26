from flask_sqlalchemy import SQLAlchemy

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
    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Float, nullable=False)
    from flask_sqlalchemy import SQLAlchemy
    