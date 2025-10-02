import os, sys, math, json, requests
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values

# --- Config PG desde .env ---
PGHOST = os.getenv("PGHOST", "db")
PGDATABASE = os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE", "ev_db")
PGUSER = os.getenv("POSTGRES_USER") or os.getenv("PGUSER", "ev_user")
PGPASSWORD = os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD", "ev_pass")
PGPORT = int(os.getenv("POSTGRES_PORT", "5432"))

# --- URL Socrata (rows.json con meta+data) ---
DATA_URL = os.getenv(
    "EV_DATA_URL",
    "https://data.wa.gov/api/views/f6w7-q2d2/rows.json?accessType=DOWNLOAD"
)

TABLE = "ev.ev_registrations"

def get_conn():
    return psycopg2.connect(
        host=PGHOST, port=PGPORT, dbname=PGDATABASE, user=PGUSER, password=PGPASSWORD
    )

def fetch_rows_json(url: str):
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    j = r.json()
    # Esperamos j["meta"]["view"]["columns"] + j["data"]
    cols = j["meta"]["view"]["columns"]
    data = j["data"]
    # mapear fieldName -> index
    field_to_idx = {}
    for idx, c in enumerate(cols):
        # columnas "meta" tienen dataTypeName meta_data y no aparecen en data
        if "fieldName" in c and not c.get("flags") == ["hidden"]:
            field_to_idx[c["fieldName"]] = idx
    return field_to_idx, data

def safe_get(row, idx, default=None):
    try:
        return row[idx]
    except Exception:
        return default

def parse_point(obj):
    """Socrata point: {'type':'Point','coordinates':[lon,lat]}"""
    if not obj:
        return None, None
    try:
        coords = obj.get("coordinates")
        if not coords or len(coords) != 2:
            return None, None
        lon, lat = coords
        return float(lat), float(lon)
    except Exception:
        return None, None

def normalize_ev_type(s):
    if not s:
        return None
    s = str(s).strip()
    if s.startswith("Battery Electric"):
        return "Battery Electric Vehicle (BEV)"
    if s.startswith("Plug-in Hybrid"):
        return "Plug-in Hybrid Electric Vehicle (PHEV)"
    return s  # por si el dataset ya viene con el texto exacto

def to_int(x):
    try:
        if x in (None, ""): return None
        return int(str(x).strip())
    except Exception:
        return None

def to_num(x):
    try:
        if x in (None, ""): return None
        return float(str(x).replace(",","").strip())
    except Exception:
        return None

def main():
    print(f"Descargando dataset: {DATA_URL}")
    field_idx, data = fetch_rows_json(DATA_URL)
    # Campos esperados (fieldName de Socrata)
    # vin_1_10, county, city, state, zip_code, model_year, make, model, ev_type,
    # cafv_type, electric_range, base_msrp, legislative_district, dol_vehicle_id,
    # geocoded_column(point), electric_utility
    f = field_idx  # alias corto

    rows = []
    for r in data:
        # NOTA: el array r incluye meta al inicio; por eso usamos índices de 'columns'
        vin_1_10 = safe_get(r, f.get("vin_1_10"))
        county = safe_get(r, f.get("county"))
        city = safe_get(r, f.get("city"))
        state = safe_get(r, f.get("state"))
        zip_code = safe_get(r, f.get("zip_code"))
        model_year = to_int(safe_get(r, f.get("model_year")))
        make = safe_get(r, f.get("make"))
        model = safe_get(r, f.get("model"))
        ev_type = normalize_ev_type(safe_get(r, f.get("ev_type")))
        cafv_type = safe_get(r, f.get("cafv_type"))
        electric_range = to_int(safe_get(r, f.get("electric_range")))
        base_msrp = to_num(safe_get(r, f.get("base_msrp")))
        legislative_district = safe_get(r, f.get("legislative_district"))
        dol_vehicle_id = safe_get(r, f.get("dol_vehicle_id"))
        point_obj = safe_get(r, f.get("geocoded_column"))
        # geocoded_column viene como dict; si viniese como string, intenta parsear
        if isinstance(point_obj, str):
            try:
                point_obj = json.loads(point_obj)
            except Exception:
                point_obj = None
        lat, lon = parse_point(point_obj)
        electric_utility = safe_get(r, f.get("electric_utility"))

        rows.append((
            dol_vehicle_id, vin_1_10,
            county, city, state, zip_code, legislative_district,
            lat, lon,
            model_year, make, model, ev_type,
            cafv_type, electric_range, base_msrp,
            electric_utility
        ))

    print(f"Filas a procesar: {len(rows)}")

    # Insert/Upsert en lotes
    cols_sql = (
        "dol_vehicle_id, vin_1_10, county, city, state, zip_code, legislative_district, "
        "latitude, longitude, model_year, make, model, ev_type, "
        "cafv_type, electric_range, base_msrp, electric_utility"
    )
    insert_sql = f"""
        INSERT INTO {TABLE} ({cols_sql})
        VALUES %s
        ON CONFLICT (dol_vehicle_id) DO UPDATE SET
          vin_1_10 = EXCLUDED.vin_1_10,
          county = EXCLUDED.county,
          city = EXCLUDED.city,
          state = EXCLUDED.state,
          zip_code = EXCLUDED.zip_code,
          legislative_district = EXCLUDED.legislative_district,
          latitude = EXCLUDED.latitude,
          longitude = EXCLUDED.longitude,
          model_year = EXCLUDED.model_year,
          make = EXCLUDED.make,
          model = EXCLUDED.model,
          ev_type = EXCLUDED.ev_type,
          cafv_type = EXCLUDED.cafv_type,
          electric_range = EXCLUDED.electric_range,
          base_msrp = EXCLUDED.base_msrp,
          electric_utility = EXCLUDED.electric_utility
    """

    BATCH = 1000
    conn = get_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            for i in range(0, len(rows), BATCH):
                chunk = rows[i:i+BATCH]
                execute_values(cur, insert_sql, chunk, page_size=BATCH)
                print(f"Upsert lote {i//BATCH + 1} -> {len(chunk)} filas")
        conn.commit()
        print("Carga completada ✅")
    except Exception as e:
        conn.rollback()
        print(f"Error durante carga: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()