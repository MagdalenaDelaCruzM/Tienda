from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, Producto, Venta

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
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Verificar credenciales (esto es solo para pruebas, mejorar en producción)
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Credenciales incorrectas.', 'danger')
    return render_template('login.html')

# Logout de administrador
@app.route('/logout')
def logout():
    session.pop('admin', None)
    flash('Sesión cerrada exitosamente.', 'info')
    return redirect(url_for('index'))

# Panel de administración
@app.route('/admin')
def admin_panel():
    if not session.get('admin'):
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('login'))

    productos = Producto.query.all()
    return render_template('admin.html', productos=productos)

@app.route('/admin/agregar', methods=['GET', 'POST'])
def agregar_producto():
    if not session.get('admin'):  # Verifica si el administrador está logueado
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        try:
            # Recibe los datos del formulario
            nombre = request.form['nombre']
            precio = float(request.form['precio'])  # Convierte el precio a float
            stock = int(request.form['stock'])  # Convierte el stock a int

            # Crea un nuevo objeto Producto
            nuevo_producto = Producto(nombre=nombre, precio=precio, stock=stock)
            
            # Agrega el nuevo producto a la sesión de la base de datos
            db.session.add(nuevo_producto)
            db.session.commit()

            flash('Producto agregado con éxito.', 'success')  # Mensaje de éxito
            return redirect(url_for('admin'))  # Redirige al panel de administración
        except Exception as e:
            flash(f'Error al agregar el producto: {str(e)}', 'danger')  # Muestra mensaje de error
    return render_template('agregar_producto.html')  # Muestra el formulario de agregar producto

# Editar un producto
@app.route('/admin/editar/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    if not session.get('admin'):
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('login'))

    producto = Producto.query.get_or_404(id)
    if request.method == 'POST':
        try:
            producto.nombre = request.form['nombre']
            producto.precio = float(request.form['precio'])
            producto.stock = int(request.form['stock'])

            if producto.precio <= 0 or producto.stock < 0:
                flash('El precio y el stock deben ser valores positivos.', 'warning')
                return redirect(url_for('editar_producto', id=id))

            db.session.commit()
            flash('Producto actualizado con éxito.', 'success')
            return redirect(url_for('admin'))
        except Exception as e:
            flash(f'Error al actualizar el producto: {str(e)}', 'danger')
    return render_template('editar_producto.html', producto=producto)

# Eliminar un producto
@app.route('/admin/eliminar/<int:id>', methods=['POST'])
def eliminar_producto(id):
    if not session.get('admin'):
        flash('Acceso no autorizado.', 'danger')
        return redirect(url_for('login'))

    try:
        producto = Producto.query.get_or_404(id)
        db.session.delete(producto)
        db.session.commit()
        flash('Producto eliminado con éxito.', 'success')
    except Exception as e:
        flash(f'Error al eliminar el producto: {str(e)}', 'danger')

    return redirect(url_for('admin'))

# Panel del cliente
@app.route('/cliente')
def cliente():
    productos = Producto.query.all()
    carrito = session.get('carrito', [])
    total = sum(item['cantidad'] * item['precio'] for item in carrito)
    return render_template('cliente.html', productos=productos, carrito=carrito, total=total)

# Agregar producto al carrito
@app.route('/cliente/comprar/<int:id>', methods=['POST'])
def agregar_carrito(id):
    producto = Producto.query.get(id)
    if not producto:
        flash('Producto no encontrado.', 'danger')
        return redirect(url_for('cliente'))

    cantidad = int(request.form.get('cantidad', 0))
    if cantidad <= 0 or cantidad > producto.stock:
        flash(f'Cantidad inválida. Stock disponible: {producto.stock}.', 'warning')
        return redirect(url_for('cliente'))

    carrito = session.setdefault('carrito', [])
    for item in carrito:
        if item['id'] == id:
            item['cantidad'] += cantidad
            break
    else:
        carrito.append({'id': producto.id, 'nombre': producto.nombre, 'precio': producto.precio, 'cantidad': cantidad})

    session.modified = True
    flash(f'{producto.nombre} agregado al carrito.', 'success')
    return redirect(url_for('cliente'))

# Comprar productos del carrito
@app.route('/cliente/carrito', methods=['GET', 'POST'])
def carrito():
    carrito = session.get('carrito', [])
    total = sum(item['cantidad'] * item['precio'] for item in carrito)

    if request.method == 'POST':
        metodo_pago = request.form.get('metodo_pago')
        if not metodo_pago:
            flash('Seleccione un método de pago.', 'warning')
            return redirect(url_for('carrito'))

        try:
            for item in carrito:
                producto = Producto.query.get(item['id'])
                if item['cantidad'] > producto.stock:
                    flash(f'Stock insuficiente para {producto.nombre}.', 'danger')
                    return redirect(url_for('carrito'))

                producto.stock -= item['cantidad']
                nueva_venta = Venta(
                    producto_id=producto.id,
                    cantidad=item['cantidad'],
                    total=item['cantidad'] * producto.precio
                )
                db.session.add(nueva_venta)

            db.session.commit()
            session.pop('carrito', None)
            flash('Compra realizada con éxito.', 'success')
            return redirect(url_for('ticket'))
        except Exception as e:
            flash(f'Error al procesar la compra: {str(e)}', 'danger')

    return render_template('carrito.html', carrito=carrito, total=total)

@app.route('/cliente/carrito/eliminar/<int:id>', methods=['POST'])
def eliminar_del_carrito(id):
    carrito = session.get('carrito', [])
    session['carrito'] = [item for item in carrito if item['id'] != id]
    session.modified = True
    flash('Producto eliminado del carrito.', 'info')
    return redirect(url_for('carrito'))


if __name__ == '__main__':
    app.run(debug=True)
