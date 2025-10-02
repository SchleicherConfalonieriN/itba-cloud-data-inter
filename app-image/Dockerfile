FROM python:3.10-slim
WORKDIR /app

COPY app-image/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY scripts /app/scripts

# Importante: NO fijes /app/scripts/02_load_data.py aquí
ENTRYPOINT ["python"]
# Sin CMD por defecto (así le pasamos el script a ejecutar en docker run)