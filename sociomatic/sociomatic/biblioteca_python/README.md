# Sistema Biblioteca Python

Aplicacion local en Python + SQLite para administrar socios y cuotas de biblioteca.

## Ejecutar

```powershell
cd C:\Users\david\OneDrive\Documents\Bibloteca\sociomatic\sociomatic\biblioteca_python
python server.py
```

Luego abrir:

```text
http://127.0.0.1:8765
```

La base local se crea automaticamente en:

```text
data\biblioteca.sqlite3
```

## Subir a la nube

Opcion recomendada para pruebas:

1. Crear un repositorio en GitHub.
2. Subir este proyecto.
3. En Render, crear un servicio web conectado al repositorio.
4. Usar:
   - Root Directory: `sociomatic/sociomatic/biblioteca_python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python server.py`

El servidor toma automaticamente el puerto de la variable `PORT`, que Render configura al publicar.

Importante: la base SQLite local (`data\biblioteca.sqlite3`) no se sube a GitHub. Para pruebas simples Render crea una base nueva. Para datos reales conviene usar un disco persistente o migrar la base a Postgres.

## Estructura MVC

```text
app\
  controllers\   Rutas y acciones HTTP
  models\        SQLite, consultas y reglas de negocio
  views\         Render de impresion
static\          HTML, CSS y JS de la interfaz
server.py        Arranque del servidor local
```

## Incluye

- Alta de socios con numero automatico reutilizable.
- Modificacion de todos los datos excepto el numero de socio.
- Baja de socio: desaparece del listado, libera el numero y elimina sus cuotas.
- Consulta de cuotas adeudadas y pagas por adelantado.
- Generacion mensual de cuotas para cobrador 1 y 3.
- Registro de cuotas pagadas, atrasadas o adelantadas.
- Impresion A4: cuatro cupones por hoja, mitad para socio y mitad para biblioteca.
