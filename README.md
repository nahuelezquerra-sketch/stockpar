# StockPar

Sistema de gestión de repuestos importados con costos en dólares
y precios de venta en pesos argentinos.

Alumno: Nahuel Ignacio Ezquerra  
Comisión: ACN4AP  
Materia: Análisis y Metodología de Sistemas

## Tecnologías

- Python y Flask.
- Flask-SQLAlchemy y SQLite.
- Flask-Login.
- Jinja2 y Bootstrap.
- API REST con respuestas JSON y autenticación mediante token.

## Funciones implementadas

- Inicio y cierre de sesión.
- Roles Administrador y Vendedor.
- Alta y consulta de proveedores.
- Alta y búsqueda de repuestos por código, nombre o marca.
- Alertas de stock mínimo.
- Reposición de stock por el Administrador.
- Registro manual e historial del dólar.
- Cálculo de precios en pesos según costo, dólar y margen.
- Creación de presupuestos con varios repuestos.
- Conservación del dólar y los precios históricos.
- Confirmación de ventas con descuento de stock.
- Rechazo de ventas sin stock suficiente.
- Prevención de descuentos duplicados.
- Cancelación de presupuestos en borrador.
- Consultas, creación y confirmación de presupuestos mediante API.

## Organización MVC

- `models/`: entidades, relaciones y reglas de datos.
- `templates/`: vistas HTML.
- `controllers/`: rutas, validaciones y operaciones.
- `app.py`: configuración e integración de los componentes.
- `static/`: recursos estáticos.
- `src/`: prototipo inicial del primer parcial.

## Instalación en Windows

Descargar el repositorio y abrir una terminal en su carpeta principal.

Crear el entorno virtual:

```powershell
python -m venv .venv
```

Instalar las dependencias:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Crear un usuario:

```powershell
.\.venv\Scripts\python.exe -m flask --app app crear-usuario
```

Completar nombre, email, rol y contraseña.
Los roles disponibles son `ADMINISTRADOR` y `VENDEDOR`.
La contraseña debe tener al menos 8 caracteres y no se muestra al escribirla.

Ejecutar:

```powershell
.\.venv\Scripts\python.exe app.py
```

Abrir http://127.0.0.1:5050 y mantener la terminal abierta.

Las tablas se crean automáticamente al cargar la aplicación.
La base de datos y la clave de sesión se generan en `instance/`.
Una instalación nueva comienza sin usuarios ni datos comerciales.

Bootstrap se carga desde un CDN y requiere conexión a internet
para mostrar los estilos.

## Prueba inicial

1. Crear un Administrador e iniciar sesión.
2. Registrar un proveedor.
3. Registrar repuestos asociados a ese proveedor.
4. Cargar una cotización manual del dólar indicando su fuente.
5. Crear un presupuesto con cantidades.
6. Confirmarlo y comprobar el descuento de stock.

Los valores del dólar utilizados en las pruebas son datos de ejemplo.

## Cálculo de precios

Precio de venta ARS = costo USD × dólar × (1 + margen / 100).

Los importes se manejan con Decimal y columnas Numeric.
Cada presupuesto conserva el dólar y los precios usados al crearlo.

## API implementada

Prefijo: `/api/v1`

| Método | Ruta | Función |
|---|---|---|
| POST | `/auth/login` | Obtener token |
| GET | `/repuestos` | Consultar repuestos activos |
| GET | `/repuestos?q=RP-001` | Buscar repuestos |
| GET | `/cotizaciones-dolar/vigente` | Consultar dólar vigente |
| POST | `/cotizaciones` | Crear presupuesto |
| GET | `/cotizaciones/{id}` | Consultar presupuesto |
| POST | `/cotizaciones/{id}/confirmar` | Confirmar venta |

### Autenticación

Enviar a `POST /api/v1/auth/login`:

```json
{
  "email": "email-del-usuario",
  "password": "contraseña-del-usuario"
}
```

La respuesta contiene `access_token`, `token_type` y `expires_in`.
El token vence después de 3600 segundos.

En las solicitudes autenticadas, enviar:

```text
Authorization: Bearer TOKEN_OBTENIDO
```

Las consultas también aceptan la sesión web.
Crear presupuestos y confirmar ventas por API requieren token.

### Crear un presupuesto

Enviar a `POST /api/v1/cotizaciones`:

```json
{
  "cliente_nombre": "Taller de prueba",
  "cliente_contacto": "Contacto de prueba",
  "items": [
    {
      "id_repuesto": 1,
      "cantidad": 2
    }
  ]
}
```

El identificador debe corresponder a un repuesto activo.
El servidor calcula los precios: el cliente no los establece.
Crear el presupuesto no descuenta stock.

Los importes se devuelven como cadenas decimales para conservar precisión.

## Validaciones verificadas manualmente

- Rechazo de CUIT duplicado.
- Restricciones de acceso según rol.
- Búsqueda por código.
- Detección de stock bajo.
- Conservación de precios históricos al actualizar el dólar.
- Descuento de stock al confirmar una venta.
- Rechazo por stock insuficiente.
- Rechazo de una segunda confirmación.
- Cancelación de borradores sin modificar stock.
- Consulta y operaciones de API con token.

## Pendientes

- Edición y desactivación de proveedores y repuestos.
- Ajustes negativos de stock e historial de movimientos.
- Rutas administrativas restantes de la API diseñada en el primer parcial.
- Completar las evidencias del tablero Kanban y los sprints.
- Pruebas automatizadas y configuración para producción.

## Alcance de ejecución

Aplicación académica para demostración local.
Se ejecuta con el servidor de desarrollo de Flask.
Las fechas se almacenan y muestran en UTC.

No se incluyen datos de usuarios, contraseñas, tokens ni claves
en el repositorio. Tampoco se suben el entorno virtual,
la base de datos local ni archivos SQL.