import uuid
import os
from datetime import datetime
from fastapi import FastAPI, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import engine, Base, get_db, SessionLocal
from .models import Run, RunCreate, RunResponse, RunResultResponse
from .pipeline.fetch_geo import fetch_and_prepare_data, get_geo_groups
from .pipeline.deseq2_runner import run_deseq2_pipeline, get_top_degs
from .pipeline.integrate import run_integration

Base.metadata.create_all(bind=engine)

# Ensure is_cancer column exists for existing SQLite databases
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE runs ADD COLUMN is_cancer BOOLEAN DEFAULT 0"))
        conn.commit()
    except Exception:
        pass

app = FastAPI(title="OmniGeneDB API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

default_work_dir = "/app/data/runs" if os.path.exists("/app/data") else os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "runs")
WORK_DIR = os.environ.get("DATA_DIR", default_work_dir)
os.makedirs(WORK_DIR, exist_ok=True)
app.mount("/plots", StaticFiles(directory=WORK_DIR), name="plots")

def run_full_pipeline(run_id: str, accession: str, case_group: str, control_group: str, top_n: int, is_cancer: bool):
    # This runs in the background with dedicated session lifecycle
    db = SessionLocal()
    db_run = None
    try:
        db_run = db.query(Run).filter(Run.id == run_id).first()
        if not db_run:
            return
        
        # Step 1: Fetch and Prepare
        db_run.status = "fetching_geo"
        db.commit()
        counts_path, coldata_path, symbol_map = fetch_and_prepare_data(
            accession=accession,
            case_group=case_group,
            control_group=control_group,
            work_dir=WORK_DIR
        )
        
        # Step 2: DESeq2 Analysis
        db_run.status = "analyzing_deseq2"
        db.commit()
        deseq_out_path = os.path.join(WORK_DIR, accession, "deseq_results.csv")
        run_deseq2_pipeline(counts_path, coldata_path, deseq_out_path)
        
        # Step 3: Get Top DEGs
        deg_list = get_top_degs(deseq_out_path, symbol_map, top_n=top_n)
        
        # Step 4: Integration
        db_run.status = "integrating_databases"
        db.commit()
        integrated_results = run_integration(deg_list, is_cancer=is_cancer)
        
        # Read MCPcounter results
        mcp_path = os.path.join(WORK_DIR, accession, "mcp_results.csv")
        if os.path.exists(mcp_path):
            try:
                import pandas as pd
                mcp_df = pd.read_csv(mcp_path, index_col=0)
                integrated_results["immune_fractions"] = mcp_df.to_dict()
            except Exception as e:
                print("Failed to load mcp_results", e)
                
        # Step 5: Save Results
        db_run.status = "completed"
        db_run.results = integrated_results
        db.commit()
        
    except Exception as e:
        if db_run:
            db_run.status = "failed"
            db_run.error_message = str(e)
            try:
                db.commit()
            except Exception:
                db.rollback()
    finally:
        db.close()


@app.get("/geo/groups/{accession}")
def fetch_groups(accession: str):
    return get_geo_groups(accession)

@app.post("/runs", response_model=RunResponse)
def submit_run(run_in: RunCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    run_id = str(uuid.uuid4())
    
    db_run = Run(
        id=run_id,
        accession=run_in.accession,
        case_group=run_in.case_group,
        control_group=run_in.control_group,
        top_n=run_in.top_n,
        is_cancer=run_in.is_cancer,
        status="queued"
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    
    background_tasks.add_task(
        run_full_pipeline, 
        run_id, 
        run_in.accession, 
        run_in.case_group, 
        run_in.control_group,
        run_in.top_n,
        run_in.is_cancer
    )
    
    return db_run

@app.get("/runs", response_model=list[RunResponse])
def get_runs(db: Session = Depends(get_db)):
    runs = db.query(Run).order_by(Run.created_at.desc()).all()
    return runs

@app.get("/runs/{run_id}", response_model=RunResponse)
def get_run_status(run_id: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@app.get("/runs/{run_id}/results", response_model=RunResultResponse)
def get_run_results(run_id: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status == "failed":
        raise HTTPException(status_code=400, detail=run.error_message or "Run failed")
    if run.status != "completed":
        raise HTTPException(status_code=400, detail="Results not ready yet")
    return run

@app.delete("/runs/{run_id}")
def delete_run(run_id: str, db: Session = Depends(get_db)):
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    db.delete(run)
    db.commit()
    return {"status": "deleted"}
