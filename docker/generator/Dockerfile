FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for MariaDB client
RUN apt-get update && \
    apt-get install -y \
    pkg-config \
    libmariadb-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY qv.py .
COPY template.plt .

# Create volume mount point for generated files
VOLUME ["/app/output"]

# Create output directory
RUN mkdir -p /app/output

# Set default command
CMD ["python", "qv.py"]
