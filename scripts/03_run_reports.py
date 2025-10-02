# scripts/03_run_reports.py
import os
import psycopg2
import pandas as pd

# --- Config PG desde .env (o defaults razonables) ---
PGHOST = os.getenv("PGHOST", "db")  # nombre del servicio en docker-compose
PGPORT = int(os.getenv("POSTGRES_PORT", "5432"))
PGDATABASE = os.getenv("POSTGRES_DB", "ev_db")
PGUSER = os.getenv("POSTGRES_USER", "ev_user")
PGPASSWORD = os.getenv("POSTGRES_PASSWORD", "ev_pass")

# Parámetros para limitar tamaño de los reportes (ajustables por ENV)
TOP_N_COUNTIES = int(os.getenv("TOP_N_COUNTIES", "20"))
TOP_N_PER_CITY = int(os.getenv("TOP_N_PER_CITY", "5"))
TOP_N_UTILITIES = int(os.getenv("TOP_N_UTILITIES", "20"))

def run_query(sql: str, params=None) -> pd.DataFrame:
    conn = psycopg2.connect(
        host=PGHOST, port=PGPORT, dbname=PGDATABASE, user=PGUSER, password=PGPASSWORD
    )
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()

def print_section(title: str):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)

def main():
    # 1) Condados con mayor cantidad de EVs registrados
    print_section(f"1) Top {TOP_N_COUNTIES} counties by EV registrations")
    q1 = f"""
        SELECT
          COALESCE(county, 'Unknown') AS county,
          COUNT(*) AS ev_count
        FROM ev.ev_registrations
        WHERE state = 'WA'  -- el dataset puede traer otros estados en algunos registros
        GROUP BY county
        ORDER BY ev_count DESC, county ASC
        LIMIT {TOP_N_COUNTIES};
    """
    df1 = run_query(q1)
    print(df1.to_string(index=False))

    # 2) Marcas y modelos más comunes por ciudad (Top N por ciudad)
    print_section(f"2) Top {TOP_N_PER_CITY} makes/models per city (most common)")
    q2 = f"""
        WITH base AS (
          SELECT
            COALESCE(city, 'Unknown')    AS city,
            COALESCE(make, 'Unknown')    AS make,
            COALESCE(model, 'Unknown')   AS model,
            COUNT(*)                     AS n
          FROM ev.ev_registrations
          WHERE state = 'WA'
            AND city IS NOT NULL AND make IS NOT NULL AND model IS NOT NULL
          GROUP BY 1,2,3
        ),
        ranked AS (
          SELECT
            city, make, model, n,
            ROW_NUMBER() OVER (PARTITION BY city ORDER BY n DESC, make, model) AS rn
          FROM base
        )
        SELECT city, make, model, n
        FROM ranked
        WHERE rn <= {TOP_N_PER_CITY}
        ORDER BY city, n DESC, make, model;
    """
    df2 = run_query(q2)
    # Mostrar agrupado por ciudad
    for city, g in df2.groupby("city", sort=True):
        print(f"\nCity: {city}")
        print(g.drop(columns=["city"]).to_string(index=False))

    # 3) Autonomía (electric_range) promedio: BEV vs PHEV
    print_section("3) Average electric range: BEV vs PHEV")
    q3 = """
        SELECT
          ev_type,
          COUNT(*)                         AS vehicles,
          AVG(electric_range)::numeric(10,2) AS avg_electric_range,
          PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY electric_range) AS median_range
        FROM ev.ev_registrations
        WHERE electric_range IS NOT NULL
          AND ev_type IN ('Battery Electric Vehicle (BEV)', 'Plug-in Hybrid Electric Vehicle (PHEV)')
        GROUP BY ev_type
        ORDER BY ev_type;
    """
    df3 = run_query(q3)
    print(df3.to_string(index=False))

    # 4) Relación MSRP y zona geográfica (ZIP): stats por ZIP
    print_section("4) MSRP by ZIP code (count, avg, median, p90)")
    q4 = """
        SELECT
          zip_code,
          COUNT(*)                                           AS n,
          AVG(base_msrp)::numeric(12,2)                      AS avg_msrp,
          PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY base_msrp)::numeric(12,2) AS median_msrp,
          PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY base_msrp)::numeric(12,2) AS p90_msrp
        FROM ev.ev_registrations
        WHERE base_msrp IS NOT NULL
          AND zip_code IS NOT NULL
        GROUP BY zip_code
        HAVING COUNT(*) >= 10            -- evitar ruido de zips con muy pocos registros
        ORDER BY avg_msrp DESC
        LIMIT 50;
    """
    df4 = run_query(q4)
    print(df4.to_string(index=False))

    # 5) Electric utilities con más EVs y su distribución por county
    print_section(f"5a) Top {TOP_N_UTILITIES} electric utilities by EV count")
    q5a = f"""
        SELECT
          COALESCE(electric_utility, 'Unknown') AS electric_utility,
          COUNT(*) AS ev_count
        FROM ev.ev_registrations
        GROUP BY electric_utility
        ORDER BY ev_count DESC, electric_utility
        LIMIT {TOP_N_UTILITIES};
    """
    df5a = run_query(q5a)
    print(df5a.to_string(index=False))

    print_section("5b) Distribution by county (top 5 per utility)")
    q5b = """
        WITH base AS (
          SELECT
            COALESCE(electric_utility, 'Unknown') AS electric_utility,
            COALESCE(county, 'Unknown')           AS county,
            COUNT(*)                               AS n
          FROM ev.ev_registrations
          GROUP BY 1,2
        ),
        ranked AS (
          SELECT
            electric_utility, county, n,
            ROW_NUMBER() OVER (PARTITION BY electric_utility ORDER BY n DESC, county) AS rn
          FROM base
        )
        SELECT electric_utility, county, n
        FROM ranked
        WHERE rn <= 5
        ORDER BY electric_utility, n DESC, county;
    """
    df5b = run_query(q5b)
    # Imprimir agrupado por utility
    for util, g in df5b.groupby("electric_utility", sort=True):
        print(f"\nUtility: {util}")
        print(g.drop(columns=["electric_utility"]).to_string(index=False))

if __name__ == "__main__":
    main()