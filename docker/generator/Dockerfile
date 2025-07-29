FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for MariaDB, and gnuplot
RUN apt-get update && \
    apt-get install -y \
    pkg-config \
    libmariadb-dev \
    gcc \
    gnuplot \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY qv.py .
COPY template.plt .

# Create output directory and set proper permissions
RUN mkdir -p /app/output && chmod 755 /app/output

# Create volume mount point for generated files
VOLUME ["/app/output"]

# Set default command
CMD ["python", "qv.py"]
