#!/usr/bin/env bash
# ==============================================================================
# OmniGeneDB — Single-Command Google Cloud Run Deployment Script
# Deploys backend (FastAPI + R DESeq2) and frontend (React Nginx reverse proxy)
# with Google Cloud Storage FUSE persistent volume mounting.
# ==============================================================================

set -euo pipefail

# ANSI color codes
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}${BOLD}======================================================================${NC}"
echo -e "${BLUE}${BOLD}        OmniGeneDB — Google Cloud Run Automated Deployer               ${NC}"
echo -e "${BLUE}${BOLD}======================================================================${NC}"

# 1. Verify gcloud CLI availability
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}[ERROR] Google Cloud SDK ('gcloud') is not installed or not in PATH.${NC}"
    echo -e "Please install it from https://cloud.google.com/sdk/docs/install and run 'gcloud auth login'."
    exit 1
fi

# 2. Check active authentication
ACTIVE_ACCOUNT=$(gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>/dev/null || true)
if [ -z "$ACTIVE_ACCOUNT" ]; then
    echo -e "${YELLOW}[WARNING] No active gcloud authentication detected. Initiating login...${NC}"
    gcloud auth login
    ACTIVE_ACCOUNT=$(gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2>/dev/null || true)
fi
echo -e "Authenticated as: ${GREEN}${ACTIVE_ACCOUNT}${NC}"

# 3. Determine Project ID
CONFIG_PROJECT=$(gcloud config get-value project 2>/dev/null || true)
if [ "$CONFIG_PROJECT" = "(unset)" ]; then
    CONFIG_PROJECT=""
fi

PROJECT_ID="${1:-${GCP_PROJECT_ID:-$CONFIG_PROJECT}}"

if [ -z "$PROJECT_ID" ]; then
    read -rp "Enter your Google Cloud Project ID: " PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}[ERROR] GCP Project ID is required to deploy.${NC}"
    exit 1
fi

gcloud config set project "$PROJECT_ID" >/dev/null

# 4. Configuration defaults
REGION="${REGION:-${2:-us-central1}}"
REPO_NAME="${REPO_NAME:-omnigenedb-repo}"
BUCKET_NAME="${BUCKET_NAME:-omnigenedb-data-${PROJECT_ID}}"

echo -e "Target Project:   ${GREEN}${PROJECT_ID}${NC}"
echo -e "Target Region:    ${GREEN}${REGION}${NC}"
echo -e "Storage Bucket:   ${GREEN}gs://${BUCKET_NAME}${NC}"
echo -e "Artifact Repo:    ${GREEN}${REPO_NAME}${NC}"
echo -e "----------------------------------------------------------------------"

# 5. Enable Required Google Cloud APIs
echo -e "\n${BLUE}[1/6] Enabling required Google Cloud APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    storage.googleapis.com

# 6. Ensure Artifact Registry Docker Repository Exists
echo -e "\n${BLUE}[2/6] Ensuring Artifact Registry repository '${REPO_NAME}' exists...${NC}"
if ! gcloud artifacts repositories describe "$REPO_NAME" --location="$REGION" &>/dev/null; then
    echo "Creating Docker repository in Artifact Registry..."
    gcloud artifacts repositories create "$REPO_NAME" \
        --repository-format=docker \
        --location="$REGION" \
        --description="OmniGeneDB Container Images"
else
    echo "Artifact Registry repository '${REPO_NAME}' is ready."
fi

# 7. Ensure Persistent Storage Bucket Exists and Set IAM Permissions
echo -e "\n${BLUE}[3/6] Configuring Cloud Storage FUSE persistent bucket (gs://${BUCKET_NAME})...${NC}"
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" &>/dev/null; then
    echo "Creating Cloud Storage bucket for persistent database and plots..."
    gcloud storage buckets create "gs://${BUCKET_NAME}" \
        --location="$REGION" \
        --uniform-bucket-level-access
else
    echo "Cloud Storage bucket 'gs://${BUCKET_NAME}' already exists."
fi

# Grant Cloud Run service account access to bucket
PROJECT_NUM=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
RUN_SERVICE_ACCOUNT="${PROJECT_NUM}-compute@developer.gserviceaccount.com"
echo "Granting storage.objectAdmin permission to default service account (${RUN_SERVICE_ACCOUNT})..."
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
    --member="serviceAccount:${RUN_SERVICE_ACCOUNT}" \
    --role="roles/storage.objectAdmin" >/dev/null

# 8. Build Backend Container Image via Cloud Build
BACKEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/backend:latest"
echo -e "\n${BLUE}[4/6] Building Backend container via Google Cloud Build...${NC}"
echo "Image tag: ${BACKEND_IMAGE}"
gcloud builds submit backend \
    --tag="$BACKEND_IMAGE" \
    --timeout=1800s

# Deploy Backend Service to Cloud Run
echo -e "\n${BLUE}Deploying 'omnigenedb-backend' to Cloud Run...${NC}"
gcloud run deploy omnigenedb-backend \
    --image="$BACKEND_IMAGE" \
    --platform=managed \
    --region="$REGION" \
    --allow-unauthenticated \
    --execution-environment=gen2 \
    --no-cpu-throttling \
    --min-instances=1 \
    --max-instances=1 \
    --memory=4Gi \
    --cpu=2 \
    --timeout=3600 \
    --add-volume="name=omni-storage,type=cloud-storage,bucket=${BUCKET_NAME}" \
    --add-volume-mount="volume=omni-storage,mount-path=/app/data" \
    --set-env-vars="PORT=8080,DATABASE_URL=sqlite:////app/data/omnigenedb.sqlite,DATA_DIR=/app/data/runs"

# Capture live backend URL
BACKEND_URL=$(gcloud run services describe omnigenedb-backend --platform managed --region="$REGION" --format='value(status.url)')
echo -e "Backend Service deployed successfully: ${GREEN}${BACKEND_URL}${NC}"

# 9. Build Frontend Container Image via Cloud Build
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/frontend:latest"
echo -e "\n${BLUE}[5/6] Building Frontend container via Google Cloud Build...${NC}"
echo "Image tag: ${FRONTEND_IMAGE}"
gcloud builds submit frontend \
    --tag="$FRONTEND_IMAGE" \
    --timeout=600s

# Deploy Frontend Service to Cloud Run
echo -e "\n${BLUE}Deploying 'omnigenedb-frontend' to Cloud Run with BACKEND_URL injected...${NC}"
gcloud run deploy omnigenedb-frontend \
    --image="$FRONTEND_IMAGE" \
    --platform=managed \
    --region="$REGION" \
    --allow-unauthenticated \
    --port=8080 \
    --memory=512Mi \
    --cpu=1 \
    --timeout=600 \
    --set-env-vars="PORT=8080,BACKEND_URL=${BACKEND_URL}"

# Capture live frontend URL
FRONTEND_URL=$(gcloud run services describe omnigenedb-frontend --platform managed --region="$REGION" --format='value(status.url)')

# 10. Summary and Verification
echo -e "\n${BLUE}[6/6] Verifying deployment health...${NC}"
if command -v curl &> /dev/null; then
    BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/runs" || echo "failed")
    echo "Backend /runs HTTP response status: ${BACKEND_HEALTH}"
fi

echo -e "\n${GREEN}${BOLD}======================================================================${NC}"
echo -e "${GREEN}${BOLD}               OMNIGENEDB DEPLOYMENT SUCCESSFUL!                      ${NC}"
echo -e "${GREEN}${BOLD}======================================================================${NC}"
echo -e "Live Application UI:  ${BOLD}${BLUE}${FRONTEND_URL}${NC}"
echo -e "Backend API Service:  ${BLUE}${BACKEND_URL}${NC}"
echo -e "Persistent Storage:   ${BLUE}gs://${BUCKET_NAME} mounted at /app/data${NC}"
echo -e ""
echo -e "Next steps:"
echo -e "1. Open ${FRONTEND_URL} in your browser to access the OmniGeneDB interface."
echo -e "2. Inspect historical runs (GSE270967) and differential expression plots."
echo -e "3. Submit a new GEO accession to run the full DESeq2 pipeline."
echo -e "${GREEN}${BOLD}======================================================================${NC}"
