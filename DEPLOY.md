# OmniGeneDB Deployment Guide (Docker Compose & Google Cloud Run)

This guide provides end-to-end instructions for running OmniGeneDB locally via **Docker Compose** and deploying it to **Google Cloud Run** for production and academic demonstration.

---

## Architecture Overview

OmniGeneDB uses a **Dual Container Service with Nginx Reverse Proxy Architecture**:

```
[ User Web Browser ]
        │
        │ HTTP (Local: port 80) / HTTPS (Cloud Run)
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Frontend Service: omnigenedb-frontend (Nginx Alpine)       │
│  - Serves compiled React 19 + TypeScript SPA at /           │
│  - Reverse-proxies /runs, /geo, /plots to ${BACKEND_URL}    │
│  - Supports TLS SNI (proxy_ssl_server_name on) for GCP      │
└─────────────────────────────────────────────────────────────┘
        │
        │ Internal Network / HTTPS Service Call
        ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend Service: omnigenedb-backend (FastAPI + Embedded R) │
│  - Python 3.11 FastAPI REST API                             │
│  - Bioconductor 3.18 runtime (DESeq2, clusterProfiler, etc.)│
│  - Persistent Volume at /app/data:                          │
│      • SQLite Database: /app/data/omnigenedb.sqlite         │
│      • Pipeline Runs & Plots: /app/data/runs/               │
│  - Automatic Seeding from /app/seed/ on initial boot        │
└─────────────────────────────────────────────────────────────┘
```

### Key Architectural Advantages
1. **Zero CORS Friction:** The browser interacts exclusively with the frontend origin. All API requests (`/runs`, `/geo/groups/...`) and plot images (`/plots/...`) are routed through the reverse proxy.
2. **Zero Hardcoded Localhost:** All URLs are dynamic and configured via environment variables.
3. **Optimized Resource Allocation:** Lightweight Nginx frontend (256–512 MiB RAM, 1 vCPU) and compute-heavy scientific backend (4 GiB RAM, 2 vCPUs) scale independently.
4. **Durable Persistence on Serverless:** Pipeline results survive container lifecycles via Cloud Storage FUSE mounts and auto-seeding.

---

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Step 1: Local Docker Compose Quickstart](#step-1-local-docker-compose-quickstart)
3. [Step 2: Single-Command GCP Deploy (`deploy.sh` & `deploy.bat`)](#step-2-single-command-gcp-deploy)
4. [Step 3: Step-by-Step Manual GCP Cloud Run Deployment](#step-3-step-by-step-manual-gcp-cloud-run-deployment)
5. [Step 4: Persistent Storage on GCP (Cloud Storage FUSE Mount)](#step-4-persistent-storage-on-gcp)
6. [Step 5: Environment Variables Reference](#step-5-environment-variables-reference)
7. [Step 6: Verification & End-to-End Testing](#step-6-verification--end-to-end-testing)
8. [Step 7: Troubleshooting Guide](#step-7-troubleshooting-guide)

---

## Prerequisites

Before beginning, ensure your environment meets these requirements:

### For Local Docker Execution
- **Docker Engine & Docker Compose (v2.0+):** Installed and running (Docker Desktop on Windows/macOS, or Docker engine on Linux).

### For Google Cloud Run Deployment
- **Google Cloud SDK (`gcloud` CLI):** Installed and added to system `PATH` ([Installation Guide](https://cloud.google.com/sdk/docs/install)).
- **GCP Authentication:** Run `gcloud auth login` to authenticate with your Google account.
- **GCP Project:** An active GCP project with billing enabled.
- **Permissions:** Your user or service account requires `Owner` or `Editor` roles (specifically Cloud Run Admin, Storage Admin, Artifact Registry Admin, and Cloud Build Editor).

---

## Step 1: Local Docker Compose Quickstart

To spin up the entire application locally with a single command:

```bash
docker compose up --build
```

To run in the background (detached mode):
```bash
docker compose up --build -d
```

### Accessing the Local Services
| Service | URL | Description |
|---|---|---|
| **Frontend Web UI** | `http://localhost` (or `http://localhost:80`) | Main application interface |
| **Backend API Docs** | `http://localhost:8000/docs` (or `http://localhost:8002/docs`) | Interactive Swagger/OpenAPI documentation |
| **API Health Endpoint** | `http://localhost:8000/runs` | Returns historical run records in JSON |
| **Sample Plot Image** | `http://localhost/plots/GSE270967/volcano.png` | Reverse-proxied plot visualization |

### Verifying Local Volume Persistence
In `docker-compose.yml`, volumes are bind-mounted directly to your host filesystem:
- `./backend/data/runs` is mounted to `/app/data/runs`
- `./backend/omnigenedb.sqlite` is mounted to `/app/data/omnigenedb.sqlite`

Any differential expression run submitted through `http://localhost` immediately writes its count matrices, DESeq2 statistics, and volcano/PCA plots to `./backend/data/runs/<accession>/` on your host machine.

### Submitting a Benchmark Run (`GSE270967`)
1. Open `http://localhost` in your web browser.
2. Select **"Submit Run"** from the navigation bar.
3. Enter GEO Accession: `GSE270967`.
4. Click **"Fetch Samples & Metadata"** (retrieves RNA-seq metadata from NCBI GEO).
5. Assign Sample Groups:
   - **Group 1 (Treatment / Tumor):** `GSM8369651`, `GSM8369652`, `GSM8369653`
   - **Group 2 (Control / Normal):** `GSM8369654`, `GSM8369655`, `GSM8369656`
6. Click **"Execute Analysis Pipeline"**.
7. Observe real-time status transitions:
   `queued` ➔ `fetching_geo` ➔ `analyzing_deseq2` ➔ `integrating_databases` ➔ `completed`.
8. Once completed, review interactive volcano plots, PCA scatter plots, GO & KEGG enrichment diagrams, and external database annotations (UniProt, OpenTargets, KEGG, STRING).

### Stopping the Local Containers
```bash
docker compose down
```
To remove volumes and reset local cache:
```bash
docker compose down -v
```

---

## Step 2: Single-Command GCP Deploy

We provide fully automated single-command deployment scripts for Linux/macOS/Cloud Shell and Windows. These scripts automate API enablement, repository creation, Cloud Storage bucket provisioning, Cloud Build compilation, Cloud Run service deployments, and service linking.

### Linux / macOS / Google Cloud Shell (`deploy.sh`)

```bash
# Make script executable
chmod +x deploy.sh

# Run with your GCP Project ID
./deploy.sh YOUR_PROJECT_ID
```
*(If no project ID is provided as an argument, the script will automatically use your active `gcloud` project or prompt you).*

### Windows Command Prompt / PowerShell (`deploy.bat`)

```cmd
deploy.bat YOUR_PROJECT_ID
```
*(Or double-click `deploy.bat` in File Explorer; it will detect your authenticated project or prompt for input).*

### What the Deployment Scripts Automate
1. **CLI & Auth Verification:** Confirms `gcloud` is installed and authenticated.
2. **API Enablement:** Enables `run.googleapis.com`, `artifactregistry.googleapis.com`, `cloudbuild.googleapis.com`, and `storage.googleapis.com`.
3. **Artifact Registry Setup:** Creates `omnigenedb-repo` Docker repository in Artifact Registry.
4. **Cloud Storage FUSE Bucket:** Creates `gs://omnigenedb-data-${PROJECT_ID}` with uniform bucket-level access and grants `roles/storage.objectAdmin` to the Cloud Run compute service account.
5. **Backend Build & Deploy:**
   - Submits `backend/` to Google Cloud Build (compiling Python + R Bioconductor).
   - Deploys `omnigenedb-backend` with 4 GiB RAM, 2 vCPUs, `--no-cpu-throttling`, 1-hour timeout, and FUSE mount at `/app/data`.
   - Captures the live HTTPS backend URL (`BACKEND_URL`).
6. **Frontend Build & Deploy:**
   - Submits `frontend/` to Google Cloud Build (compiling React SPA into Nginx image).
   - Deploys `omnigenedb-frontend` with injected `BACKEND_URL=${BACKEND_URL}`.
7. **Live Verification:** Verifies `/runs` health endpoint and prints public application URLs.

---

## Step 3: Step-by-Step Manual GCP Cloud Run Deployment

If you prefer to run each step manually, follow this exact sequence:

### 3.1. Set Environment Variables
```bash
export PROJECT_ID="YOUR_PROJECT_ID"
export REGION="us-central1"
export REPO_NAME="omnigenedb-repo"
export BUCKET_NAME="omnigenedb-data-${PROJECT_ID}"

gcloud config set project ${PROJECT_ID}
```

### 3.2. Enable Required GCP APIs
```bash
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  storage.googleapis.com
```

### 3.3. Create Artifact Registry Repository
```bash
gcloud artifacts repositories create ${REPO_NAME} \
  --repository-format=docker \
  --location=${REGION} \
  --description="OmniGeneDB Container Images" \
  || true
```

### 3.4. Provision Cloud Storage Bucket for Persistent FUSE Mount
```bash
# 1. Create bucket
gcloud storage buckets create gs://${BUCKET_NAME} \
  --location=${REGION} \
  --uniform-bucket-level-access \
  || true

# 2. Grant Cloud Run default service account permission to write to bucket
PROJECT_NUM=$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')
gcloud storage buckets add-iam-policy-binding gs://${BUCKET_NAME} \
  --member="serviceAccount:${PROJECT_NUM}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"
```

### 3.5. Build and Deploy the Backend Service
```bash
export BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/backend:latest"

# Build container image remotely using Google Cloud Build
echo "Building backend container..."
gcloud builds submit backend --tag ${BACKEND_IMAGE} --timeout=1800s

# Deploy backend to Cloud Run
echo "Deploying backend service..."
gcloud run deploy omnigenedb-backend \
  --image=${BACKEND_IMAGE} \
  --platform=managed \
  --region=${REGION} \
  --allow-unauthenticated \
  --execution-environment=gen2 \
  --no-cpu-throttling \
  --min-instances=1 \
  --max-instances=1 \
  --memory=4Gi \
  --cpu=2 \
  --timeout=3600 \
  --add-volume=name=omni-storage,type=cloud-storage,bucket=${BUCKET_NAME} \
  --add-volume-mount=volume=omni-storage,mount-path=/app/data \
  --set-env-vars="PORT=8080,DATABASE_URL=sqlite:////app/data/omnigenedb.sqlite,DATA_DIR=/app/data/runs"

# Retrieve live Backend URL
export BACKEND_URL=$(gcloud run services describe omnigenedb-backend --platform managed --region=${REGION} --format='value(status.url)')
echo "Backend live at: ${BACKEND_URL}"
```

### 3.6. Build and Deploy the Frontend Service
```bash
export FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/frontend:latest"

# Build frontend container image remotely using Google Cloud Build
echo "Building frontend container..."
gcloud builds submit frontend --tag ${FRONTEND_IMAGE} --timeout=600s

# Deploy frontend with BACKEND_URL injected
echo "Deploying frontend service..."
gcloud run deploy omnigenedb-frontend \
  --image=${FRONTEND_IMAGE} \
  --platform=managed \
  --region=${REGION} \
  --allow-unauthenticated \
  --port=8080 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=600 \
  --set-env-vars="PORT=8080,BACKEND_URL=${BACKEND_URL}"

# Retrieve live Frontend URL
export FRONTEND_URL=$(gcloud run services describe omnigenedb-frontend --platform managed --region=${REGION} --format='value(status.url)')
echo "Application UI live at: ${FRONTEND_URL}"
```

---

## Step 4: Persistent Storage on GCP

### Ephemeral Storage vs Cloud Storage FUSE
Cloud Run instances utilize an ephemeral sandbox filesystem. Standard container writes are lost when containers restart, scale down, or update.

OmniGeneDB overcomes this limitation using **Cloud Storage FUSE Volume Mounts**:
- The GCS bucket (`gs://omnigenedb-data-${PROJECT_ID}`) is mounted directly to `/app/data` inside the container using Cloud Run Second Generation (`gen2`) execution environment.
- The SQLite database is located at `/app/data/omnigenedb.sqlite`.
- Plot files and downloaded GEO series matrices are saved under `/app/data/runs/<accession>/`.

### Automatic Seeding (`docker-entrypoint.sh`)
When a brand-new Cloud Storage bucket is mounted to `/app/data`, the directory is initially empty. OmniGeneDB solves this via an automated seeding pattern:
1. During image build (`backend/Dockerfile`), precomputed benchmark datasets (`GSE270967`) and the initial SQLite database are baked into `/app/seed/`.
2. On boot, `backend/docker-entrypoint.sh` checks if `/app/data` is empty:
   ```sh
   if [ -z "$(ls -A /app/data 2>/dev/null)" ]; then
       echo "[docker-entrypoint] /app/data is empty. Initializing from /app/seed..."
       cp -r /app/seed/* /app/data/
   fi
   ```
3. If empty, the demo data is copied into the persistent volume, guaranteeing immediate out-of-the-box demo functionality.
4. If `/app/data` already contains user data, seeding is skipped, preserving existing user runs.

### SQLite Durability & Single-Instance Concurrency
Because Cloud Storage FUSE does not support distributed POSIX byte-range file locking across separate compute nodes, the backend Cloud Run service enforces:
```bash
--min-instances=1 --max-instances=1
```
This guarantees that a single compute instance handles SQLite writes, preventing file lock contention while maintaining instant responsiveness without cold starts.

---

## Step 5: Environment Variables Reference

### Backend Service (`omnigenedb-backend`)
| Variable | Default (Local) | Default (Cloud Run) | Description |
|---|---|---|---|
| `PORT` | `8000` | `8080` | Port on which Uvicorn ASGI server listens. Automatically provided by Cloud Run. |
| `DATABASE_URL` | `sqlite:////app/data/omnigenedb.sqlite` | `sqlite:////app/data/omnigenedb.sqlite` | SQLAlchemy database connection URI. Points to persistent mount. |
| `DATA_DIR` | `/app/data/runs` | `/app/data/runs` | Filesystem directory where GEO matrices, DESeq2 CSV outputs, and PNG plots are written. |
| `PYTHONUNBUFFERED` | `1` | `1` | Forces unbuffered stdout/stderr for immediate Cloud Logging output. |

### Frontend Service (`omnigenedb-frontend`)
| Variable | Default (Local) | Default (Cloud Run) | Description |
|---|---|---|---|
| `PORT` | `80` | `8080` | Port on which Nginx listens. Substituted into `default.conf` template on container startup. |
| `BACKEND_URL` | `http://backend:8000` | `https://<backend-cloudrun-url>` | Upstream target for Nginx reverse proxy. On Cloud Run, points to backend HTTPS service. |
| `VITE_API_URL` | `""` | `""` | Build argument for Vite. Leaving empty enables relative URL routing (`/runs`, `/geo`, `/plots`). |

---

## Step 6: Verification & End-to-End Testing

### 1. Verify Backend Health
```bash
# Check JSON run records
curl -f "${BACKEND_URL}/runs"
```
*Expected Result:* Returns HTTP 200 with JSON list containing historical runs (e.g., `GSE270967`).

### 2. Verify Reverse Proxy & Static Plot Delivery
```bash
# Verify volcano plot delivery through the frontend reverse proxy
curl -I "${FRONTEND_URL}/plots/GSE270967/volcano.png"
```
*Expected Result:* Returns `HTTP/1.1 200 OK` or `HTTP/2 200` with `content-type: image/png`.

### 3. Verify End-to-End Analysis Pipeline
1. Open `${FRONTEND_URL}` in your web browser.
2. Confirm that the benchmark run `GSE270967` appears in the "Runs History" table.
3. Click into `GSE270967` to inspect:
   - Volcano plot displaying differential expression significance.
   - PCA plot demonstrating separation between treatment and control cohorts.
   - GO & KEGG enrichment diagrams.
   - Interactive data table with annotated gene symbols, log2 fold changes, and p-values.
4. Submit a new analysis run to confirm the full DESeq2 pipeline executes end-to-end.

---

## Step 7: Troubleshooting Guide

### Issue 1: DESeq2 Pipeline Freezes or Hangs on `analyzing_deseq2`
- **Cause:** Cloud Run by default throttles CPU allocations when no active HTTP request is being processed. Because OmniGeneDB runs DESeq2 as a FastAPI `BackgroundTask`, CPU throttling freezes the R process.
- **Solution:** Ensure `--no-cpu-throttling` is specified on `omnigenedb-backend`:
  ```bash
  gcloud run services update omnigenedb-backend --region=us-central1 --no-cpu-throttling
  ```

### Issue 2: 504 Gateway Timeout on Large Accessions
- **Cause:** Downloading large GEO SOFT matrices or executing DESeq2 takes longer than the default Cloud Run timeout (300 seconds).
- **Solution:** Set Cloud Run request timeout to 3600 seconds (1 hour):
  ```bash
  gcloud run services update omnigenedb-backend --region=us-central1 --timeout=3600
  ```

### Issue 3: Missing Images in Web UI (`404 Not Found` on `/plots/...`)
- **Cause:** Frontend reverse proxy is not forwarding `/plots` to the backend, or backend `DATA_DIR` does not match the plot mount directory.
- **Solution:**
  1. Confirm `frontend/nginx.conf.template` includes `location ~ ^/(runs|geo|plots)`.
  2. Confirm backend environment variable has `DATA_DIR=/app/data/runs`.
  3. Ensure Cloud Storage bucket mount is active at `/app/data`.

### Issue 4: SQLite Database Locked Error (`sqlite3.OperationalError: database is locked`)
- **Cause:** Multiple Cloud Run backend instances writing concurrently over Cloud Storage FUSE.
- **Solution:** Enforce `--max-instances 1` on `omnigenedb-backend`:
  ```bash
  gcloud run services update omnigenedb-backend --region=us-central1 --max-instances=1
  ```

### Issue 5: Port 80 Already in Use Locally (Windows / macOS)
- **Cause:** Local IIS, Skype, or another web server is bound to port 80.
- **Solution:** Change the host port mapping in `docker-compose.yml` or run:
  ```bash
  FRONTEND_PORT=3000 docker compose up
  ```
  Then access the frontend at `http://localhost:3000`.

---

## Summary of Files & Locations

| File | Purpose | Location |
|---|---|---|
| `docker-compose.yml` | Multi-container local orchestration (ports 80 & 8000) | Project Root |
| `deploy.sh` | Linux/macOS/Cloud Shell automated GCP deploy script | Project Root |
| `deploy.bat` | Windows automated GCP deploy batch script | Project Root |
| `DEPLOY.md` | Comprehensive deployment guide and reference manual | Project Root |
| `.dockerignore` | Build context exclusions for Docker and Cloud Build | Project Root |
| `backend/Dockerfile` | Python 3.11 + Bioconductor 3.18 multi-runtime container | `backend/` |
| `backend/docker-entrypoint.sh`| Storage auto-seeding and Uvicorn process launcher | `backend/` |
| `frontend/Dockerfile` | Node 22 build + Nginx Alpine production server | `frontend/` |
| `frontend/nginx.conf.template`| Dynamic reverse proxy and SPA routing template | `frontend/` |
