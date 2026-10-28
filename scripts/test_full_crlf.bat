@echo off
rem ==============================================================================
rem OmniGeneDB — Windows Single-Command Google Cloud Run Deployment Batch Script
rem Deploys backend (FastAPI + R DESeq2) and frontend (React Nginx reverse proxy)
rem with Google Cloud Storage FUSE persistent volume mounting.
rem ==============================================================================

setlocal enabledelayedexpansion

echo ======================================================================
echo         OmniGeneDB -- Google Cloud Run Automated Deployer
echo ======================================================================
echo.

rem 1. Check for gcloud CLI
where gcloud >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Google Cloud SDK 'gcloud' is not found in PATH.
    echo Please install Google Cloud SDK from https://cloud.google.com/sdk/docs/install
    pause
    exit /b 1
)

rem 2. Check active authentication
for /f "tokens=*" %%a in ('gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2^>nul') do set ACTIVE_ACCOUNT=%%a
if "%ACTIVE_ACCOUNT%"=="" (
    echo [WARNING] No active gcloud account detected. Opening login...
    call gcloud auth login
    for /f "tokens=*" %%a in ('gcloud auth list --filter="status:ACTIVE" --format="value(account)" 2^>nul') do set ACTIVE_ACCOUNT=%%a
)
echo Authenticated as: %ACTIVE_ACCOUNT%

rem 3. Detect or prompt for GCP Project ID
set PROJECT_ID=%~1
if "%PROJECT_ID%"=="" (
    for /f "tokens=*" %%i in ('gcloud config get-value project 2^>nul') do set PROJECT_ID=%%i
)
if "%PROJECT_ID%"=="(unset)" set PROJECT_ID=
if "%PROJECT_ID%"=="" (
    set /p PROJECT_ID="Enter your Google Cloud Project ID: "
)
if "%PROJECT_ID%"=="" (
    echo [ERROR] GCP Project ID is required to deploy.
    pause
    exit /b 1
)

call gcloud config set project %PROJECT_ID% >nul 2>&1

rem 4. Configuration defaults
set REGION=%~2
if "%REGION%"=="" set REGION=us-central1
set REPO_NAME=omnigenedb-repo
set BUCKET_NAME=omnigenedb-data-%PROJECT_ID%

echo Target Project:   %PROJECT_ID%
echo Target Region:    %REGION%
echo Storage Bucket:   gs://%BUCKET_NAME%
echo Artifact Repo:    %REPO_NAME%
echo ----------------------------------------------------------------------
echo.

rem 5. Enable Required Google Cloud APIs
echo [1/6] Enabling required Google Cloud APIs...
call gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com storage.googleapis.com

rem 6. Ensure Artifact Registry repository exists
echo [2/6] Ensuring Artifact Registry repository '%REPO_NAME%' exists...
call gcloud artifacts repositories describe %REPO_NAME% --location=%REGION% >nul 2>&1
if %errorlevel% neq 0 (
    echo Creating Docker repository in Artifact Registry...
    call gcloud artifacts repositories create %REPO_NAME% --repository-format=docker --location=%REGION% --description="OmniGeneDB Container Images"
) else (
    echo Artifact Registry repository '%REPO_NAME%' is ready.
)

rem 7. Ensure Persistent Storage Bucket exists and grant IAM permissions
echo [3/6] Configuring Cloud Storage FUSE persistent bucket (gs://%BUCKET_NAME%)...
call gcloud storage buckets describe gs://%BUCKET_NAME% >nul 2>&1
if %errorlevel% neq 0 (
    echo Creating Cloud Storage bucket for persistent database and plots...
    call gcloud storage buckets create gs://%BUCKET_NAME% --location=%REGION% --uniform-bucket-level-access
) else (
    echo Cloud Storage bucket 'gs://%BUCKET_NAME%' already exists.
)

for /f "tokens=*" %%p in ('gcloud projects describe %PROJECT_ID% --format="value(projectNumber)"') do set PROJECT_NUM=%%p
set RUN_SERVICE_ACCOUNT=%PROJECT_NUM%-compute@developer.gserviceaccount.com
echo Granting storage.objectAdmin to service account %RUN_SERVICE_ACCOUNT%...
call gcloud storage buckets add-iam-policy-binding gs://%BUCKET_NAME% --member="serviceAccount:%RUN_SERVICE_ACCOUNT%" --role="roles/storage.objectAdmin" >nul 2>&1

rem 8. Build Backend Container Image via Cloud Build
set BACKEND_IMAGE=%REGION%-docker.pkg.dev/%PROJECT_ID%/%REPO_NAME%/backend:latest
echo.
echo [4/6] Building Backend container via Google Cloud Build...
echo Image tag: %BACKEND_IMAGE%
call gcloud builds submit backend --tag %BACKEND_IMAGE% --timeout=1800s
if %errorlevel% neq 0 (
    echo [ERROR] Backend container build failed.
    pause
    exit /b %errorlevel%
)

echo Deploying 'omnigenedb-backend' to Cloud Run...
call gcloud run deploy omnigenedb-backend --image=%BACKEND_IMAGE% --platform=managed --region=%REGION% --allow-unauthenticated --execution-environment=gen2 --no-cpu-throttling --min-instances=1 --max-instances=1 --memory=4Gi --cpu=2 --timeout=3600 --add-volume=name=omni-storage,type=cloud-storage,bucket=%BUCKET_NAME% --add-volume-mount=volume=omni-storage,mount-path=/app/data --set-env-vars="PORT=8080,DATABASE_URL=sqlite:////app/data/omnigenedb.sqlite,DATA_DIR=/app/data/runs"
if %errorlevel% neq 0 (
    echo [ERROR] Backend deployment failed.
    pause
    exit /b %errorlevel%
)

for /f "tokens=*" %%u in ('gcloud run services describe omnigenedb-backend --platform=managed --region=%REGION% --format="value(status.url)"') do set BACKEND_URL=%%u
echo Backend Service live at: %BACKEND_URL%

rem 9. Build Frontend Container Image via Cloud Build
set FRONTEND_IMAGE=%REGION%-docker.pkg.dev/%PROJECT_ID%/%REPO_NAME%/frontend:latest
echo.
echo [5/6] Building Frontend container via Google Cloud Build...
echo Image tag: %FRONTEND_IMAGE%
call gcloud builds submit frontend --tag %FRONTEND_IMAGE% --timeout=600s
if %errorlevel% neq 0 (
    echo [ERROR] Frontend container build failed.
    pause
    exit /b %errorlevel%
)

echo Deploying 'omnigenedb-frontend' to Cloud Run with BACKEND_URL injected...
call gcloud run deploy omnigenedb-frontend --image=%FRONTEND_IMAGE% --platform=managed --region=%REGION% --allow-unauthenticated --port=8080 --memory=512Mi --cpu=1 --timeout=600 --set-env-vars="PORT=8080,BACKEND_URL=%BACKEND_URL%"
if %errorlevel% neq 0 (
    echo [ERROR] Frontend deployment failed.
    pause
    exit /b %errorlevel%
)

for /f "tokens=*" %%u in ('gcloud run services describe omnigenedb-frontend --platform=managed --region=%REGION% --format="value(status.url)"') do set FRONTEND_URL=%%u

rem 10. Summary and Live URLs
echo.
echo [6/6] Verifying deployment...
echo ======================================================================
echo                OMNIGENEDB DEPLOYMENT SUCCESSFUL!
echo ======================================================================
echo Live Application UI:  %FRONTEND_URL%
echo Backend API Service:  %BACKEND_URL%
echo Persistent Storage:   gs://%BUCKET_NAME% mounted at /app/data
echo.
echo Next steps:
echo 1. Open %FRONTEND_URL% in your web browser.
echo 2. Inspect historical runs (GSE270967) and differential expression plots.
echo 3. Submit a new GEO accession to run the full DESeq2 pipeline.
echo ======================================================================
echo.
pause
