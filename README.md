# Ejercicio 6 – Documentación y ejecución end-to-end

Este ejercicio integra todo el flujo de trabajo realizado en los pasos anteriores:

1. **Levantar la base de datos en Docker Compose** (Postgres 12.7).
2. **Crear las tablas (DDL)** usando el script Bash.
3. **Construir la imagen de aplicación** con Python + dependencias.
4. **Cargar los datos** del dataset público de vehículos eléctricos de Washington.
5. **Ejecutar consultas SQL** mediante un script de reportes en Python.
6. **Mostrar todo el proceso end-to-end** desde un único script Bash (`run_all.sh`).

---

## 📂 Archivos principales

- `docker-compose.yml` → definición del servicio de Postgres.
- `.env.example` → ejemplo de configuración (usuario, password, DB, puerto).
- `scripts/01_create_tables.sh` → aplica `db/schema.sql` para crear tablas.
- `scripts/02_load_data.py` → descarga dataset y lo inserta en la base.
- `scripts/03_run_reports.py` → ejecuta consultas SQL y muestra reportes.
- `app-image/Dockerfile` y `app-image/requirements.txt` → imagen para scripts Python.
- `run_all.sh` → orquesta todos los pasos anteriores.

---

## ▶️ Ejecución end-to-end

1. Crear archivo `.env` a partir de `.env.example`:

   ```bash
   cp .env.example .env
   # editar valores si es necesario