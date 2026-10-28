import os
import sys
import uuid
import time
import json
import traceback
from datetime import datetime

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from starlette.testclient import TestClient
from app.main import app, run_full_pipeline, WORK_DIR
from app.db import SessionLocal
from app.models import Run

def run_challenger_tests():
    print("=================================================================")
    print("STARTING EMPIRICAL CHALLENGER VERIFICATION (AC 1 & AC 2)")
    print("=================================================================")
    client = TestClient(app)

    # -------------------------------------------------------------
    # AC 2: GSE15852 Microarray Graceful Handling
    # -------------------------------------------------------------
    print("\n>>> CHALLENGE 1: AC 2 - GSE15852 Microarray Graceful Handling")
    gse15852_id = f"challenger-gse15852-{uuid.uuid4()}"
    db = SessionLocal()
    run_15852 = Run(
        id=gse15852_id,
        accession="GSE15852",
        case_group="breast tumor tissue",
        control_group="normal breast tissue",
        top_n=15,
        is_cancer=True,
        status="queued"
    )
    db.add(run_15852)
    db.commit()
    db.close()

    print(f"Created queued run in DB for GSE15852: ID={gse15852_id}")
    t0 = time.time()
    try:
        run_full_pipeline(
            run_id=gse15852_id,
            accession="GSE15852",
            case_group="breast tumor tissue",
            control_group="normal breast tissue",
            top_n=15,
            is_cancer=True
        )
        print(f"run_full_pipeline executed without crashing in {time.time()-t0:.2f}s")
    except Exception as e:
        print(f"FAIL: run_full_pipeline crashed with unhandled exception: {e}")
        traceback.print_exc()
        assert False, f"Unhandled exception during GSE15852 execution: {e}"

    # Verify database state for GSE15852
    db = SessionLocal()
    rec_15852 = db.query(Run).filter(Run.id == gse15852_id).first()
    assert rec_15852 is not None, "GSE15852 run record disappeared!"
    print(f"Status in DB: {rec_15852.status}")
    print(f"Error message in DB: {rec_15852.error_message}")

    assert rec_15852.status == "failed", f"Expected status 'failed', got '{rec_15852.status}'"
    assert rec_15852.error_message is not None, "Error message must not be None"
    assert "Affymetrix" in rec_15852.error_message or "microarray" in rec_15852.error_message.lower(), (
        f"Error message does not mention microarray nature: {rec_15852.error_message}"
    )
    assert "RNA-Seq" in rec_15852.error_message or "count" in rec_15852.error_message.lower(), (
        f"Error message does not explain RNA-Seq requirement: {rec_15852.error_message}"
    )

    # Verify FastAPI HTTP API endpoints for GSE15852
    resp_status = client.get(f"/runs/{gse15852_id}")
    print(f"HTTP GET /runs/{gse15852_id} -> {resp_status.status_code}")
    assert resp_status.status_code == 200, f"Expected 200 from /runs/{gse15852_id}, got {resp_status.status_code}"
    status_json = resp_status.json()
    assert status_json["status"] == "failed"
    assert status_json["error_message"] == rec_15852.error_message

    resp_results = client.get(f"/runs/{gse15852_id}/results")
    print(f"HTTP GET /runs/{gse15852_id}/results -> {resp_results.status_code}")
    assert resp_results.status_code == 400, f"Expected 400 (graceful client error) from /results, got {resp_results.status_code}"
    assert "500" not in str(resp_results.status_code)
    results_err = resp_results.json().get("detail", "")
    print(f"API Error Detail: {results_err}")
    assert "microarray" in results_err.lower() or "gse15852" in results_err.lower()
    print("PASS: AC 2 - GSE15852 Microarray Graceful Handling VERIFIED.")

    # -------------------------------------------------------------
    # AC 1: GSE270967 Full Pipeline Execution
    # -------------------------------------------------------------
    print("\n>>> CHALLENGE 2: AC 1 - GSE270967 Full Pipeline Execution")
    gse270967_id = f"challenger-gse270967-{uuid.uuid4()}"
    run_270967 = Run(
        id=gse270967_id,
        accession="GSE270967",
        case_group="non-responder (rd)",
        control_group="responder (pcr)",
        top_n=15,
        is_cancer=True,
        status="queued"
    )
    db.add(run_270967)
    db.commit()
    db.close()

    print(f"Created queued run in DB for GSE270967: ID={gse270967_id}")
    t0 = time.time()
    try:
        run_full_pipeline(
            run_id=gse270967_id,
            accession="GSE270967",
            case_group="non-responder (rd)",
            control_group="responder (pcr)",
            top_n=15,
            is_cancer=True
        )
        print(f"run_full_pipeline executed successfully in {time.time()-t0:.2f}s")
    except Exception as e:
        print(f"FAIL: run_full_pipeline crashed with unhandled exception: {e}")
        traceback.print_exc()
        assert False, f"Unhandled exception during GSE270967 execution: {e}"

    # Verify database state for GSE270967
    db = SessionLocal()
    rec_270967 = db.query(Run).filter(Run.id == gse270967_id).first()
    assert rec_270967 is not None, "GSE270967 run record missing!"
    print(f"Status in DB: {rec_270967.status}")
    print(f"Error message: {rec_270967.error_message}")
    assert rec_270967.status == "completed", f"Expected status 'completed', got '{rec_270967.status}'"
    assert rec_270967.error_message is None, f"Expected None error_message, got '{rec_270967.error_message}'"

    # Verify FastAPI HTTP API endpoints for GSE270967
    resp_status = client.get(f"/runs/{gse270967_id}")
    assert resp_status.status_code == 200
    assert resp_status.json()["status"] == "completed"

    resp_results = client.get(f"/runs/{gse270967_id}/results")
    assert resp_results.status_code == 200, f"Expected 200, got {resp_results.status_code}: {resp_results.text}"
    data = resp_results.json()

    # Verify JSON Schema & Differential Expression Fields
    results_obj = data.get("results")
    assert results_obj is not None, "Results object is None"
    gene_items = results_obj.get("results", [])
    print(f"Returned gene item count: {len(gene_items)}")
    assert len(gene_items) > 0, "No gene items returned in results!"
    assert len(gene_items) == 15, f"Expected 15 DEGs (top_n=15), got {len(gene_items)}"

    symbols = [g.get("symbol") for g in gene_items]
    print(f"Returned gene symbols: {symbols}")

    for idx, item in enumerate(gene_items):
        sym = item.get("symbol")
        assert sym is not None and len(str(sym).strip()) > 0, f"Item {idx} missing valid symbol"
        
        # Verify differential expression fields
        assert "log2fc" in item, f"Gene {sym} missing log2fc field"
        assert "padj" in item, f"Gene {sym} missing padj field"
        assert "baseMean" in item, f"Gene {sym} missing baseMean field"
        
        # Check numeric types
        log2fc = item["log2fc"]
        padj = item["padj"]
        base_mean = item["baseMean"]
        assert log2fc is not None, f"Gene {sym} has null log2fc"
        assert isinstance(log2fc, (int, float)), f"Gene {sym} log2fc not a float: {type(log2fc)}"
        assert base_mean is not None, f"Gene {sym} has null baseMean"
        assert isinstance(base_mean, (int, float)), f"Gene {sym} baseMean not a float: {type(base_mean)}"
        assert base_mean > 0, f"Gene {sym} baseMean should be positive, got {base_mean}"

    # Verify master_tfs is non-empty
    master_tfs = results_obj.get("master_tfs", [])
    print(f"Master Transcription Factors (master_tfs): {master_tfs}")
    assert len(master_tfs) > 0, "master_tfs is empty! Enrichr ChEA 2022 integration failed."
    assert all(isinstance(tf, str) and len(tf) > 0 for tf in master_tfs), "Invalid TF entry format"

    # Verify eqtls are populated for annotated genes via GTEx v2
    eqtl_genes = []
    total_eqtl_count = 0
    for item in gene_items:
        eqtls = item.get("eqtl")
        if eqtls and len(eqtls) > 0:
            eqtl_genes.append(item["symbol"])
            total_eqtl_count += len(eqtls)
            # Verify structure of first eqtl
            first_eqtl = eqtls[0]
            assert "tissueSiteDetailId" in first_eqtl, f"Missing tissueSiteDetailId in eqtl for {item['symbol']}"
            assert "pValue" in first_eqtl, f"Missing pValue in eqtl for {item['symbol']}"

    print(f"Genes with populated GTEx v2 eQTLs ({len(eqtl_genes)}/{len(gene_items)}): {eqtl_genes}")
    print(f"Total eQTL records across annotated genes: {total_eqtl_count}")
    assert len(eqtl_genes) > 0, "Zero genes had populated eQTLs! GTEx v2 integration failed."
    assert total_eqtl_count > 0, "Total eQTL count is zero."

    # Verify plot files generation
    run_plot_dir = os.path.join(WORK_DIR, "GSE270967")
    plots_to_check = {
        "volcano.png": 10000,
        "pca.png": 10000,
        "go_enrichment.png": 10000,
        "kegg_enrichment.png": 10000
    }
    print(f"\nChecking plot artifacts in: {run_plot_dir}")
    for plot_name, min_size in plots_to_check.items():
        plot_path = os.path.join(run_plot_dir, plot_name)
        assert os.path.isfile(plot_path), f"Plot {plot_name} does not exist at {plot_path}"
        plot_sz = os.path.getsize(plot_path)
        print(f"  {plot_name}: {plot_sz:,} bytes (min threshold: {min_size:,} bytes)")
        assert plot_sz >= min_size, f"Plot {plot_name} size ({plot_sz}) below threshold {min_size}"

    # Verify plot HTTP static serving
    for plot_name in plots_to_check.keys():
        plot_resp = client.get(f"/plots/GSE270967/{plot_name}")
        assert plot_resp.status_code == 200, f"Static route /plots/GSE270967/{plot_name} returned {plot_resp.status_code}"
        assert plot_resp.headers.get("content-type") == "image/png"
        assert len(plot_resp.content) > 0

    print("PASS: AC 1 - GSE270967 Full Pipeline Execution VERIFIED.")

    # -------------------------------------------------------------
    # CHALLENGE 3: Stress-Testing Edge Cases
    # -------------------------------------------------------------
    print("\n>>> CHALLENGE 3: Stress-Testing Edge Cases & Adversarial Inputs")

    # 3.1 Non-existent Run ID 404 behavior
    bad_id = str(uuid.uuid4())
    assert client.get(f"/runs/{bad_id}").status_code == 404
    assert client.get(f"/runs/{bad_id}/results").status_code == 404

    # 3.2 In-progress Run 400 behavior (not 500)
    pending_id = f"test-pending-{uuid.uuid4()}"
    p_run = Run(
        id=pending_id,
        accession="GSE270967",
        case_group="A",
        control_group="B",
        status="analyzing_deseq2"
    )
    db.add(p_run)
    db.commit()
    resp_pending = client.get(f"/runs/{pending_id}/results")
    assert resp_pending.status_code == 400
    assert "Results not ready yet" in resp_pending.json().get("detail", "")
    db.delete(p_run)
    db.commit()

    # 3.3 Strict JSON compliance of floats
    from app.pipeline.deseq2_runner import sanitize_float
    assert sanitize_float(float('nan')) is None
    assert sanitize_float(float('inf')) is None
    assert sanitize_float(float('-inf')) is None
    raw_payload = {"test_val": sanitize_float(float('nan'))}
    # This MUST serialize cleanly with allow_nan=False
    dumped = json.dumps(raw_payload, allow_nan=False)
    assert '{"test_val": null}' == dumped
    print("  Sanitize float handles NaN/Inf safely -> JSON null: PASS")

    # 3.4 Unannotated gene resilience in GTEx v2
    from app.pipeline.integrate import get_gtex_eqtls
    assert get_gtex_eqtls("LOC107985728") == []
    assert get_gtex_eqtls("999999999") == []
    assert get_gtex_eqtls("") == []
    assert get_gtex_eqtls(None) == []
    print("  GTEx v2 handles unannotated loci safely -> empty list: PASS")

    print("\n=================================================================")
    print("ALL EMPIRICAL CHALLENGES PASSED! VERDICT: APPROVE")
    print("=================================================================")

if __name__ == "__main__":
    run_challenger_tests()
