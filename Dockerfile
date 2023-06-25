# Usar la imagen de Python 3.11
FROM python:3.11

# Establecer el directorio de trabajo en /app
WORKDIR /app

# Copiar los archivos necesarios al contenedor
COPY requirements.txt .
COPY proyecto_api /app/proyecto_api

# Instalar los paquetes requeridos
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto 80 para la API
EXPOSE 80

# Ejecutar la aplicación con Waitress en el puerto 80
CMD ["waitress-serve", "--port=80", "--call", "proyecto_api:create_app"]
