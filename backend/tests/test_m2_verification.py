import os
import sys
import tempfile
import json
import uuid
import pytest

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.pipeline.integrate import (
    get_gtex_eqtls,
    get_enrichr_tfs,
    get_string_ppi,
    get_uniprot_data,
    get_uniprot_info,
    get_kegg_data,
    get_kegg_pathways,
    get_string_data,
    get_ensembl_data,
    get_clinvar_data,
    get_opentargets_data,
    get_opentargets_drugs,
    run_integration,
)
from app.pipeline.fetch_geo import (
    _fetch_matrix_metadata,
    _fetch_matrix_info,
    check_is_microarray,
    fetch_and_prepare_data,
    get_geo_groups,
)
from app.models import (
    Run,
    RunCreate,
    RunResponse,
    RunResultItem,
    RunResultData,
    RunResultResponse,
)
from app.db import SessionLocal, engine, Base
from app.main import run_full_pipeline


def test_gtex_v2_api():
    print("\n=== Test 1: GTEx API v2 Migration ===")
    
    # 1. Annotated coding gene (TP53)
    eqtls = get_gtex_eqtls("TP53")
    print(f"TP53 eQTL count: {len(eqtls)}")
    assert len(eqtls) > 0, "Expected non-empty eQTL list for TP53"
    first = eqtls[0]
    print(f"Sample eQTL entry: {first}")
    assert "tissueSiteDetailId" in first, "Missing tissueSiteDetailId"
    assert "variantId" in first or "snpId" in first, "Missing variantId/snpId"
    assert "nes" in first, "Missing nes"
    assert "pValue" in first, "Missing pValue"
    assert first["tissueSiteDetailId"] is not None
    assert first["pValue"] is not None

    # 2. Unannotated / LOC gene (LOC102723847)
    loc_eqtls = get_gtex_eqtls("LOC102723847")
    print(f"LOC102723847 eQTL count: {len(loc_eqtls)}")
    assert loc_eqtls == [], f"Expected empty list for LOC gene, got {loc_eqtls}"

    # 3. Numeric Entrez ID (105378790)
    num_eqtls = get_gtex_eqtls("105378790")
    print(f"105378790 eQTL count: {len(num_eqtls)}")
    assert num_eqtls == [], f"Expected empty list for numeric ID, got {num_eqtls}"

    # 4. None and empty string inputs
    assert get_gtex_eqtls(None) == []
    assert get_gtex_eqtls("") == []
    assert get_gtex_eqtls("   ") == []
    print("PASS: GTEx API v2 Migration\n")


def test_enrichr_chea_tfs():
    print("\n=== Test 2: Enrichr ChEA 2022 TF Analysis ===")
    
    # 1. Standard candidate symbols
    symbols = ["TP53", "CDKN1A", "MDM2", "BAX", "ERBB4"]
    tfs = get_enrichr_tfs(symbols)
    print(f"Enrichr TFs for {symbols}: {tfs}")
    assert len(tfs) > 0, "Expected non-empty master_tfs from Enrichr"
    assert all(isinstance(tf, str) and len(tf) > 0 for tf in tfs)

    # 2. Unannotated loci
    unannotated = ["LOC102723847", "105378790"]
    u_tfs = get_enrichr_tfs(unannotated)
    print(f"Enrichr TFs for unannotated: {u_tfs}")
    assert isinstance(u_tfs, list)

    # 3. Empty list / None
    assert get_enrichr_tfs([]) == []
    assert get_enrichr_tfs(None) == []
    print("PASS: Enrichr ChEA 2022 TF Analysis\n")


def test_series_matrix_header_parsing():
    print("\n=== Test 3: Series Matrix Header Parsing ===")
    meta = _fetch_matrix_metadata("GSE270967")
    assert len(meta) == 20, f"Expected 20 samples for GSE270967, got {len(meta)}"
    
    # Check that sample titles are properly populated (not empty strings)
    sample_items = list(meta.items())
    first_gsm, first_data = sample_items[0]
    print(f"Sample {first_gsm} metadata: {first_data}")
    assert first_data["title"] != "", f"Sample title for {first_gsm} must not be empty"
    assert "bcat" in first_data["title"], f"Expected 'bcat' in sample title, got '{first_data['title']}'"

    all_titles = [v["title"] for v in meta.values()]
    assert all(t != "" for t in all_titles), "All sample titles in GSE270967 must be non-empty"
    print(f"All 20 sample titles successfully parsed: {all_titles[:5]}...")
    print("PASS: Series Matrix Header Parsing\n")


def test_gse15852_microarray_graceful_handling():
    print("\n=== Test 4: GSE15852 Microarray Graceful Handling ===")
    
    # 1. Platform check detection
    is_micro, msg = check_is_microarray("GSE15852")
    print(f"check_is_microarray('GSE15852'): is_micro={is_micro}")
    print(f"Message: {msg}")
    assert is_micro is True
    expected_msg = (
        "GSE15852 is an Affymetrix microarray dataset (GPL96) with continuous hybridization intensity data. "
        "OmniGeneDB DESeq2 analysis requires raw integer RNA-Seq count matrices. "
        "Please provide an RNA-Seq accession (e.g. GSE270967) or raw count matrix."
    )
    assert msg == expected_msg

    # 2. fetch_and_prepare_data raises ValueError without falling back to 404
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            fetch_and_prepare_data(
                accession="GSE15852",
                case_group="cancer",
                control_group="normal",
                work_dir=tmpdir
            )
            assert False, "fetch_and_prepare_data should have raised ValueError on GSE15852"
        except ValueError as e:
            print(f"Caught expected ValueError: {e}")
            assert str(e) == expected_msg

    # 3. Test background execution in run_full_pipeline records failed status cleanly in database
    db = SessionLocal()
    test_run_id = f"test-m2-{uuid.uuid4()}"
    test_run = Run(
        id=test_run_id,
        accession="GSE15852",
        case_group="cancer",
        control_group="normal",
        top_n=10,
        is_cancer=True,
        status="queued"
    )
    db.add(test_run)
    db.commit()
    db.close()

    # Execute run_full_pipeline synchronously to verify DB state
    run_full_pipeline(
        run_id=test_run_id,
        accession="GSE15852",
        case_group="cancer",
        control_group="normal",
        top_n=10,
        is_cancer=True
    )

    db = SessionLocal()
    updated_run = db.query(Run).filter(Run.id == test_run_id).first()
    print(f"Database record after run_full_pipeline: status='{updated_run.status}', error='{updated_run.error_message}'")
    assert updated_run.status == "failed"
    assert updated_run.error_message == expected_msg
    
    # Cleanup test run
    db.delete(updated_run)
    db.commit()
    db.close()
    print("PASS: GSE15852 Microarray Graceful Handling\n")


def test_unannotated_loci_resilience():
    print("\n=== Test 5: Unannotated Loci & Missing Pathways Resilience ===")
    
    # Verify aliases
    assert get_uniprot_info == get_uniprot_data
    assert get_opentargets_drugs == get_opentargets_data
    assert get_kegg_pathways == get_kegg_data

    # Test individual functions with LOC and numeric genes
    loc_gene = "LOC102723847"
    num_gene = "105378790"

    assert get_uniprot_data(loc_gene) is None
    assert get_uniprot_data(num_gene) is None
    assert get_kegg_data(None) == {"pathways": [], "source_url": None}
    assert get_string_data(loc_gene)["partners"] == []
    assert get_ensembl_data(loc_gene)["location"] == "N/A"
    assert get_clinvar_data(loc_gene)["status"] in ("No variants reported", "N/A")
    assert get_opentargets_data(None) == ([], False)

    # Test run_integration with a mixed list: known gene + unannotated genes
    deg_list = [
        {"symbol": "TP53", "log2fc": 2.5, "padj": 0.001, "baseMean": 1250.0},
        {"symbol": "LOC102723847", "log2fc": -1.2, "padj": 0.04, "baseMean": 85.0},
        {"symbol": "105378790", "log2fc": 0.8, "padj": 0.05, "baseMean": 42.0},
    ]

    res = run_integration(deg_list, is_cancer=True)
    assert "results" in res
    assert "master_tfs" in res
    assert "ppi_network" in res

    results = res["results"]
    assert len(results) == 3, f"Expected all 3 genes preserved, got {len(results)}"
    
    symbols_in_res = [r["symbol"] for r in results]
    assert symbols_in_res == ["TP53", "LOC102723847", "105378790"]

    # Verify baseMean is preserved
    assert results[0]["baseMean"] == 1250.0
    assert results[1]["baseMean"] == 85.0
    assert results[2]["baseMean"] == 42.0

    # Verify TP53 has populated biological data
    assert results[0]["uniprot"] is not None
    assert len(results[0]["eqtl"]) > 0

    # Verify unannotated genes have coverage_gaps properly populated
    assert "UniProt Function" in results[1]["coverage_gaps"]
    assert "KEGG Pathways" in results[1]["coverage_gaps"]
    print("Preserved results summary:")
    for r in results:
        print(f"  {r['symbol']}: log2fc={r['log2fc']}, padj={r['padj']}, baseMean={r['baseMean']}, gaps={r['coverage_gaps']}")

    print("PASS: Unannotated Loci Resilience\n")


def test_api_models_and_session_handling():
    print("\n=== Test 6: API Models & Schema Compliance ===")

    # Test RunResponse schema includes top_n and is_cancer
    from datetime import datetime
    resp = RunResponse(
        id="test-123",
        accession="GSE270967",
        case_group="Case",
        control_group="Control",
        top_n=25,
        is_cancer=True,
        status="completed",
        created_at=datetime.utcnow()
    )
    assert resp.top_n == 25
    assert resp.is_cancer is True
    
    # Test RunResultItem schema includes padj and baseMean
    item = RunResultItem(
        symbol="TP53",
        log2fc=1.5,
        padj=0.002,
        baseMean=550.0
    )
    assert item.padj == 0.002
    assert item.baseMean == 550.0
    dumped = item.model_dump()
    assert dumped["padj"] == 0.002
    assert dumped["baseMean"] == 550.0

    # Test RunResultData with items
    data = RunResultData(
        results=[item],
        master_tfs=["TP63"]
    )
    assert len(data.results) == 1
    assert data.results[0].baseMean == 550.0

    print("PASS: API Models & Schema Compliance\n")


if __name__ == "__main__":
    test_gtex_v2_api()
    test_enrichr_chea_tfs()
    test_series_matrix_header_parsing()
    test_gse15852_microarray_graceful_handling()
    test_unannotated_loci_resilience()
    test_api_models_and_session_handling()
    print("==================================================")
    print("ALL MILESTONE M2 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("==================================================")
