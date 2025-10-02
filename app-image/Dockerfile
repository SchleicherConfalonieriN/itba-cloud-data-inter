FROM python:3.10-slim
WORKDIR /app

# copia el requirements desde la carpeta app-image usando contexto raíz
COPY app-image/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ahora sí, con contexto raíz podemos copiar ./scripts completo
COPY scripts /app/scripts

ENTRYPOINT ["python", "/app/scripts/02_load_data.py"]