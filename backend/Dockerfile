# =====================================================================
# OmniGeneDB Backend Dockerfile
# Base: Bioconductor Release 3.18 (Ubuntu 22.04 LTS, R 4.3.x)
# Provides pre-compiled Bioconductor Linux binaries and graphics libraries
# =====================================================================
FROM bioconductor/bioconductor_docker:RELEASE_3_18

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 1. Install Python 3, pip, and system development tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    curl \
    ca-certificates \
    libcurl4-openssl-dev \
    libssl-dev \
    libxml2-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libpng-dev \
    libtiff5-dev \
    libjpeg-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    zlib1g-dev \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# 2. Install required R and Bioconductor packages using pre-compiled binaries
RUN R -e 'BiocManager::install(c( \
    "DESeq2", \
    "clusterProfiler", \
    "org.Hs.eg.db", \
    "enrichplot", \
    "ggplot2", \
    "ggridges", \
    "reshape2", \
    "MCPcounter" \
), ask = FALSE, update = FALSE)'

# 3. Create application working and storage directories
WORKDIR /app
RUN mkdir -p /app/seed /app/data /app/data/runs

# 4. Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

# 5. Pre-seed demo datasets and SQLite database into /app/seed/ and /app/data/
COPY omnigenedb.sqlite /app/seed/omnigenedb.sqlite
COPY data/ /app/seed/
RUN cp -r /app/seed/* /app/data/

# 6. Copy backend application source code, verification test files, and entrypoint
COPY app/ /app/app/
COPY test_*.py /app/
COPY docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh

# 7. Configure persistent storage and runtime environment variables
ENV PORT=8000
ENV DATABASE_URL=sqlite:////app/data/omnigenedb.sqlite
ENV DATA_DIR=/app/data/runs

# Expose HTTP port
EXPOSE 8000

# 8. Entrypoint with automatic seeding and uvicorn startup
ENTRYPOINT ["/app/docker-entrypoint.sh"]
