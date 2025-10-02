## Ejercicio 6 — Documentación y ejecución end-to-end

### ¿Qué hice en cada ejercicio?

- **Ejercicio 1 (Dataset & preguntas):** Elegí el dataset público *Electric Vehicle Population Data* del DOL de Washington y definí 5 preguntas de negocio.  
  → Ver detalle en [`docs/dataset.md`](docs/dataset.md).

- **Ejercicio 2 (DB en Docker):** Provisioné **PostgreSQL 12.7** con `docker-compose.yml`, exponiendo el puerto 5432 y usando un volumen `pgdata` para persistencia.

- **Ejercicio 3 (DDL con Bash):** Creé el esquema y tabla principal (`ev.ev_registrations`) e índices en `db/schema.sql`.  
  El script [`scripts/01_create_tables.sh`](scripts/01_create_tables.sh) aplica el DDL contra el contenedor de Postgres (espera a que esté *healthy* y ejecuta con una imagen efímera de `postgres:12.7`).

- **Ejercicio 4 (Carga de datos):** Implementé [`scripts/02_load_data.py`](scripts/02_load_data.py) que descarga el JSON del dataset, normaliza campos (ej. lat/lon, rangos, MSRP) y hace *upsert* en la tabla.  
  Se ejecuta dentro de una imagen propia de Python (ver `app-image/`) mediante `docker run`.

- **Ejercicio 5 (Consultas/Reportes):** Implementé [`scripts/03_run_reports.py`](scripts/03_run_reports.py) con 5 queries SQL que responden las preguntas de negocio (condados, marcas/modelos por ciudad, BEV vs PHEV, MSRP por ZIP y utilities).  
  Imprime tablas legibles en consola y también corre en contenedor efímero.

---

### Cómo ejecutar todo el proceso end-to-end

> Requisitos: Docker + Docker Compose. Conexión a Internet para bajar imágenes y dataset.

1. **Configurar variables**  
   Crear `.env` desde el ejemplo:
   ```bash
   cp .env.example .env
   # Ajustar si es necesario: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_PORT

2. **Ejecutar el pipeline completo**  
   El archivo de Bash [`run_all.sh`](run_all.sh) orquesta todo el proceso end-to-end: levanta la DB, aplica DDL, construye la imagen, carga los datos y corre los reportes.

   ```bash
   chmod +x run_all.sh
   ./run_all.sh