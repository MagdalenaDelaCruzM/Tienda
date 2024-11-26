from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, Producto, Venta
from datetime import datetime
from flask import make_response
from xhtml2pdf import pisa
import io
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tienda.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'supersecretkey'  # Llave secreta para sesiones
db.init_app(app)

# Crear tablas en la base de datos
with app.app_context():
    db.create_all()

# Página principal
@app.route('/')
def index():
    return render_template('index.html')


# Login de administrador
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Validar credenciales (puedes cambiar esto por validación en base de datos)
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('admin_panel'))  # Redirige al panel de administración
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')  # Renderiza el formulario de inicio de sesión



# Logout de administrador
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    flash('Sesión cerrada exitosamente.', 'info')
    return redirect(url_for('index'))

# Panel de administración (protegido por autenticación)
@app.route('/admin')
def admin_panel():
    if not session.get('admin'):
        flash('Acceso no autorizado. Inicia sesión primero.', 'danger')
        return redirect(url_for('admin_login'))

    productos = Producto.query.all()
    return render_template('admin.html', productos=productos)

# Agregar producto
@app.route('/add_product', methods=['POST'])
def agregar_producto():
    nombre = request.form['nombre']
    precio = float(request.form['precio'])
    stock = int(request.form['stock'])
    imagen = request.form.get('imagen')  # URL de la imagen (opcional)

    nuevo_producto = Producto(nombre=nombre, precio=precio, stock=stock, imagen=imagen)
    db.session.add(nuevo_producto)
    db.session.commit()

    flash('Producto agregado exitosamente.', 'success')
    return redirect(url_for('admin_panel'))

from flask import request, jsonify

@app.route('/edit_product/<int:id>', methods=['POST'])
def editar_producto(id):
    producto = Producto.query.get_or_404(id)
    data = request.get_json()

    producto.nombre = data.get('nombre', producto.nombre)
    producto.precio = data.get('precio', producto.precio)
    producto.stock = data.get('stock', producto.stock)
    producto.imagen = data.get('imagen', producto.imagen)

    db.session.commit()

    return jsonify(success=True, message="Producto actualizado exitosamente")

# Eliminar producto
@app.route('/delete_product/<int:id>', methods=['POST'])
def eliminar_producto(id):
    if not session.get('admin'):
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('admin_login'))

    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado exitosamente.', 'success')
    return redirect(url_for('admin_panel'))

# Página de productos para clientes
@app.route('/cliente/productos')
def productos_cliente():
    # Filtrar productos con stock mayor a 0
    productos = Producto.query.filter(Producto.stock > 0).all()
    return render_template('clientes.html', productos=productos)


# Agregar producto al carrito
@app.route('/cliente/comprar/<int:id>', methods=['POST'])
def agregar_carrito(id):
    producto = Producto.query.get_or_404(id)
    cantidad = int(request.form.get('cantidad', 0))

    # Validar si la cantidad solicitada es válida
    if cantidad <= 0 or cantidad > producto.stock:
        flash(f"No puedes agregar más de {producto.stock} unidad(es) de {producto.nombre}.", 'danger')
        return redirect(url_for('productos_cliente'))

    # Agregar al carrito
    carrito = session.setdefault('carrito', [])
    for item in carrito:
        if item['id'] == producto.id:
            item['cantidad'] += cantidad
            
            # Asegurarse de que no exceda el stock
            if item['cantidad'] > producto.stock:
                item['cantidad'] = producto.stock
                flash(f"Cantidad ajustada al stock disponible para {producto.nombre}.", 'warning')
            break
    else:
        carrito.append({'id': producto.id, 'nombre': producto.nombre, 'precio': producto.precio, 'cantidad': cantidad})

    session.modified = True
    flash(f"{cantidad} unidad(es) de {producto.nombre} agregada(s) al carrito.", 'success')
    return redirect(url_for('productos_cliente'))

# Ver carrito
@app.route('/cliente/carrito')
def carrito():
    carrito = session.get('carrito', [])
    total = sum(item['cantidad'] * item['precio'] for item in carrito)
    return render_template('carrito.html', carrito=carrito, total=total)

@app.route('/cliente/carrito/eliminar/<int:id>', methods=['POST'])
def eliminar_del_carrito(id):
    carrito = session.get('carrito', [])
    session['carrito'] = [item for item in carrito if item['id'] != id]
    session.modified = True
    flash('Producto eliminado del carrito.', 'info')
    return redirect(url_for('carrito'))


@app.route('/cliente/carrito/confirmar', methods=['POST'])
def confirmar_compra():
    carrito = session.get('carrito', [])
    metodo_pago = request.form.get('metodo_pago')

    if not carrito:
        flash('El carrito está vacío. Agregue productos antes de confirmar la compra.', 'warning')
        return redirect(url_for('carrito'))

    try:
        total = 0
        for item in carrito:
            producto = Producto.query.get(item['id'])
            
            # Validar si hay suficiente stock
            if item['cantidad'] > producto.stock:
                flash(f"No hay suficiente stock para el producto {producto.nombre}. Stock disponible: {producto.stock}", 'danger')
                return redirect(url_for('carrito'))
            
            # Actualizar el stock
            producto.stock -= item['cantidad']
            db.session.add(producto)
            total += item['cantidad'] * producto.precio
        
        db.session.commit()

        # Generar información del ticket
        fecha_hora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        session['ticket_productos'] = carrito
        session['ticket_metodo_pago'] = metodo_pago
        session['ticket_total'] = total
        session['ticket_fecha_hora'] = fecha_hora

        # Limpiar el carrito
        session.pop('carrito', None)
        session.modified = True

        flash('Compra realizada con éxito.', 'success')
        return render_template('ticket.html', ticket={
            'productos': carrito,
            'metodo_pago': metodo_pago,
            'total': total,
            'fecha_hora': fecha_hora
        }, pdf=False)

    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar la compra: {str(e)}', 'danger')
        return redirect(url_for('carrito'))

    
@app.route('/cliente/ticket/pdf', methods=['GET'])
def generar_ticket_pdf():
    # Simular los datos del ticket (puedes adaptarlo según tu lógica)
    ticket = {
        'productos': session.get('ticket_productos', []),
        'metodo_pago': session.get('ticket_metodo_pago', ''),
        'total': session.get('ticket_total', 0.0),
        'fecha_hora': session.get('ticket_fecha_hora', '')
    }

    # Renderizar el HTML del ticket
    rendered_html = render_template('ticket.html', ticket=ticket)
    
    # Convertir el HTML a PDF
    pdf = io.BytesIO()
    pisa_status = pisa.CreatePDF(io.StringIO(rendered_html), dest=pdf)
    
    if pisa_status.err:
        return "Hubo un error al generar el PDF", 500

    # Devolver el PDF como respuesta
    pdf.seek(0)
    response = make_response(pdf.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=ticket.pdf'
    return response

@app.route('/upload_image', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        flash('No se seleccionó ningún archivo', 'danger')
        return redirect(url_for('admin_panel'))

    file = request.files['file']
    if file.filename == '':
        flash('El archivo no tiene nombre', 'danger')
        return redirect(url_for('admin_panel'))

    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join('static/images', filename))
        flash('Imagen subida exitosamente.', 'success')
        return redirect(url_for('admin_panel'))
        # Ahora puedes guardar 'ruta_imagen' en la base de datos

if __name__ == '__main__':
    app.run(debug=True)
