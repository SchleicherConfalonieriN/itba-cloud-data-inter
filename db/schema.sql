-- Schema opcional para orden
CREATE SCHEMA IF NOT EXISTS ev;

-- Tabla principal
CREATE TABLE IF NOT EXISTS ev.ev_registrations (
  id BIGSERIAL PRIMARY KEY,

  -- Identificación vehículo / registro
  dol_vehicle_id TEXT UNIQUE,             -- Unique number per DOL (puede servir como PK lógica)
  vin_1_10       TEXT,                    -- 10 primeros chars del VIN

  -- Ubicación
  county               TEXT,
  city                 TEXT,
  state                TEXT,
  zip_code             TEXT,
  legislative_district TEXT,

  -- Geolocalización (centro del ZIP). Guardamos lat/lon como NUMERIC.
  latitude   NUMERIC(9,6),
  longitude  NUMERIC(9,6),

  -- Vehículo
  model_year INTEGER,                     -- convertido desde texto a int en la carga
  make       TEXT,
  model      TEXT,
  ev_type    TEXT CHECK (ev_type IN ('Battery Electric Vehicle (BEV)', 'Plug-in Hybrid Electric Vehicle (PHEV)')),

  -- Elegibilidad e info técnica/económica
  cafv_type       TEXT,                   -- Clean Alternative Fuel Vehicle eligibility (texto categórico)
  electric_range  INTEGER,                -- millas
  base_msrp       NUMERIC(12,2),          -- precio de lista

  -- Utility
  electric_utility TEXT,

  -- Metadata opcional
  created_at TIMESTAMP DEFAULT NOW()
);

-- Índices para acelerar las preguntas de negocio
CREATE INDEX IF NOT EXISTS idx_ev_county       ON ev.ev_registrations (county);
CREATE INDEX IF NOT EXISTS idx_ev_city         ON ev.ev_registrations (city);
CREATE INDEX IF NOT EXISTS idx_ev_zip          ON ev.ev_registrations (zip_code);
CREATE INDEX IF NOT EXISTS idx_ev_make         ON ev.ev_registrations (make);
CREATE INDEX IF NOT EXISTS idx_ev_model        ON ev.ev_registrations (model);
CREATE INDEX IF NOT EXISTS idx_ev_type         ON ev.ev_registrations (ev_type);
CREATE INDEX IF NOT EXISTS idx_ev_utility      ON ev.ev_registrations (electric_utility);
CREATE INDEX IF NOT EXISTS idx_ev_model_year   ON ev.ev_registrations (model_year);

-- Índice compuesto útil para "marcas y modelos por ciudad"
CREATE INDEX IF NOT EXISTS idx_ev_city_make_model
  ON ev.ev_registrations (city, make, model);

-- Para consultas geográficas básicas por lat/lon (sin PostGIS)
CREATE INDEX IF NOT EXISTS idx_ev_lat_lon
  ON ev.ev_registrations (latitude, longitude);