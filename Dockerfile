# Base image for Python
FROM python:3.13

# Set environment variable to ensure Python output is shown in real-time
ENV PYTHONUNBUFFERED=1

# Install dependencies for GDAL, GEOS and PostgreSQL client
RUN apt-get update && apt-get install -y \
    binutils libproj-dev gdal-bin libgdal-dev libgeos-dev \
    gettext curl netcat-openbsd postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Set the GDAL and GEOS paths for Django GIS to recognize
ENV GDAL_LIBRARY_PATH=/usr/lib/libgdal.so
ENV GEOS_LIBRARY_PATH=/usr/lib/libgeos_c.so

# Set the working directory in the container
WORKDIR /app

# Copy requirements.txt into the container
COPY requirements.txt /app/

# Install any Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . /app/

# Kein CMD hier - wird durch docker-compose überschrieben