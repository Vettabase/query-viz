# Monolithic Dockerfile for query-viz generator with multi-stage builds.
# We create thes images:
#   - qv-gen-base     Base environment
#   - qv-gen-app      Daemonised application
#   - qv-gen-test     Run pytest and exit


# Stage 1: Base image with all system dependencies and application files
FROM python:3.11-slim AS qv-gen-base

LABEL org.opencontainers.image.title="Query-Viz Generator Base"
LABEL org.opencontainers.image.description="Base image for the application and test containers"
LABEL org.opencontainers.image.authors="Vettabase Ltd"
LABEL org.opencontainers.image.vendor="Vettabase Ltd"
LABEL org.opencontainers.image.licenses="AGPL 3"
LABEL org.opencontainers.image.url="https://github.com/Vettabase/query-viz/"
LABEL org.opencontainers.image.source="https://github.com/Vettabase/query-viz/"
LABEL org.opencontainers.image.documentation="https://github.com/Vettabase/query-viz/"
LABEL org.opencontainers.image.version="0.1-evergreen"

WORKDIR /app

RUN apt-get update && \
    apt-get install -y \
    pkg-config \
    libmariadb-dev \
    libpq-dev \
    gcc \
    gnuplot \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application files
COPY qv.py .
COPY chart_templates/ ./chart_templates/
COPY query_viz/ ./query_viz/

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONIOENCODING=utf-8
ENV PYTHONPATH=/app
# tells the app not to exit with non-zero code
# when it wants to avoid auto-restart
ENV IN_DOCKER=1


# Stage 2: Test image with test dependencies and test files
FROM qv-gen-base AS qv-gen-test

LABEL org.opencontainers.image.title="Query-Viz Generator Tests"
LABEL org.opencontainers.image.description="Query-Viz test image"

# Test dependencies
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# Test configuration and fixtures
COPY pytest.ini .
COPY conftest.py .
COPY tests/ ./tests/

# run pytest and generate a coverage report
CMD ["pytest", "-v", "--cov=query_viz", "--cov-report=term-missing"]


# Stage 3: Production application image
FROM qv-gen-base AS qv-gen-app

LABEL org.opencontainers.image.title="Query-Viz Generator App"
LABEL org.opencontainers.image.description="Query-Viz application image"

# Output directory
RUN mkdir -p /app/output && chmod 755 /app/output
VOLUME ["/app/output"]

CMD ["python", "-u", "qv.py", "-vv"]
