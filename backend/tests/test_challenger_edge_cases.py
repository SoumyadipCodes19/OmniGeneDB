import os
import sys
import tempfile
import json
import math
import pandas as pd
import numpy as np

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.pipeline.deseq2_runner import sanitize_float, get_top_degs
from app.pipeline.integrate import (
    get_uniprot_data,
    get_kegg_data,
    get_string_data,
    get_pdb_data,
    get_alphafold_data,
    get_ensembl_data,
    get_clinvar_data,
    get_opentargets_data,
    get_gtex_eqtls,
    get_tcga_survival,
    get_enrichr_tfs,
    get_string_ppi,
    check_consistency,
    run_integration,
)

def run_tests():
    print("======================================================================")
    print("CHALLENGER 2: EDGE-CASE EMPIRICAL STRESS TEST SUITE")
    print("======================================================================")

    # ------------------------------------------------------------------
    # Test Section 1: sanitize_float and NaN/Inf Float Compliance
    # ------------------------------------------------------------------
    print("\n--- Test 1: sanitize_float Exhaustive Stress-Testing ---")
    test_cases_nan_inf = [
        float('nan'), float('inf'), float('-inf'),
        np.nan, np.inf, -np.inf,
        pd.NA, None,
        "nan", "NaN", "NAN", "inf", "-inf", "Infinity", "-Infinity",
        "", "   ", "abc"
    ]
    for case in test_cases_nan_inf:
        res = sanitize_float(case)
        assert res is None, f"Expected None for {case!r}, got {res!r}"

    test_cases_valid = [
        (0, 0.0),
        (0.0, 0.0),
        (-0.0, 0.0),
        (123, 123.0),
        (123.456, 123.456),
        (-987.654, -987.654),
        (1e-10, 1e-10),
        (1e20, 1e20),
        ("123.45", 123.45),
        ("-0.5", -0.5),
        ("0", 0.0)
    ]
    for inp, expected in test_cases_valid:
        res = sanitize_float(inp)
        assert res == expected, f"Expected {expected} for {inp!r}, got {res!r}"

    # Test JSON compliance with allow_nan=False
    payload = {
        "nan_case": sanitize_float(float('nan')),
        "inf_case": sanitize_float(float('inf')),
        "neginf_case": sanitize_float(float('-inf')),
        "valid": sanitize_float(42.5)
    }
    dumped = json.dumps(payload, allow_nan=False)
    assert '"nan_case": null' in dumped
    assert '"inf_case": null' in dumped
    assert '"neginf_case": null' in dumped
    assert '"valid": 42.5' in dumped
    print("PASS: sanitize_float successfully converts all non-compliant values to None/null.")

    # ------------------------------------------------------------------
    # Test Section 2: deseq2_runner.py get_top_degs with Unannotated & Malformed Rows
    # ------------------------------------------------------------------
    print("\n--- Test 2: get_top_degs Stress-Testing ---")
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "stress_deseq_results.csv")
        # Build dataframe with unannotated genes, numeric IDs, lncRNAs, empty symbols, floats, and NaNs
        raw_data = {
            "GeneID": [
                "LOC102723847",     # Unannotated LOC
                "105378790",        # Numeric Entrez ID
                "LINC01914",        # lncRNA
                "NONEXISTENT_SYM",  # Nonexistent symbol
                "TP53",             # Well-annotated control
                "",                 # Empty string
                "   ",              # Whitespace only
                "12345.67",         # Float as GeneID
                "ENSG00000141510",  # Ensembl ID
                "DUPLICATE_LOC",    # Duplicate 1
                "DUPLICATE_LOC",    # Duplicate 2
                "NAN_VAL_GENE",     # NaN metrics
            ],
            "baseMean": [
                150.5,
                42.0,
                88.2,
                12.0,
                2500.0,
                0.0,
                np.nan,
                np.inf,
                1100.0,
                55.0,
                50.0,
                np.nan,
            ],
            "log2FoldChange": [
                -2.3,
                1.4,
                0.9,
                -0.4,
                3.8,
                np.nan,
                float('inf'),
                float('-inf'),
                2.1,
                -1.1,
                -1.1,
                np.nan,
            ],
            "lfcSE": [0.1] * 12,
            "stat": [2.0] * 12,
            "pvalue": [1e-5, 2e-4, 3e-3, 4e-2, 1e-12, np.nan, 0.5, 0.5, 1e-8, 0.01, 0.01, np.nan],
            "padj": [
                0.0001,
                0.002,
                0.015,
                0.08,
                1e-10,
                np.nan,
                np.nan,
                np.inf,
                0.00005,
                0.03,
                0.03,
                np.nan,
            ]
        }
        pd.DataFrame(raw_data).to_csv(csv_path, index=False)

        # Subtest 2A: get_top_degs without symbol_map (auto-query / fallback)
        degs_no_map = get_top_degs(csv_path, symbol_map=None, top_n=10)
        assert isinstance(degs_no_map, list)
        symbols_found = [d["symbol"] for d in degs_no_map]
        print(f"Returned symbols (no map): {symbols_found}")

        # Verify unannotated genes are preserved and not dropped
        assert "LOC102723847" in symbols_found, "LOC102723847 was dropped!"
        assert "105378790" in symbols_found or any("105378790" in s for s in symbols_found), "105378790 was dropped!"
        assert "LINC01914" in symbols_found, "LINC01914 was dropped!"
        assert "TP53" in symbols_found, "TP53 was dropped!"

        # Verify empty strings are excluded
        assert "" not in symbols_found
        assert "   " not in symbols_found

        # Verify JSON compliance with allow_nan=False
        dumped_json = json.dumps(degs_no_map, allow_nan=False)
        parsed = json.loads(dumped_json)
        assert len(parsed) == len(degs_no_map)
        for item in parsed:
            assert item["log2fc"] is None or isinstance(item["log2fc"], (int, float))
            assert item["padj"] is None or isinstance(item["padj"], (int, float))
            assert item["baseMean"] is None or isinstance(item["baseMean"], (int, float))

        # Subtest 2B: get_top_degs with symbol_map
        symbol_map = {
            "LOC102723847": "LOC102723847",
            "105378790": "105378790",
            "LINC01914": "LINC01914",
            "TP53": "TP53",
            "DUPLICATE_LOC": "LOC_DUP",
        }
        degs_with_map = get_top_degs(csv_path, symbol_map=symbol_map, top_n=5)
        symbols_map_found = [d["symbol"] for d in degs_with_map]
        print(f"Returned symbols (with map): {symbols_map_found}")
        assert "LOC102723847" in symbols_map_found
        assert "105378790" in symbols_map_found
        assert "LINC01914" in symbols_map_found
        assert "TP53" in symbols_map_found

        dumped_map_json = json.dumps(degs_with_map, allow_nan=False)
        assert len(json.loads(dumped_map_json)) == len(degs_with_map)
    print("PASS: get_top_degs stress test on unannotated genes and malformed floats passed.")

    # ------------------------------------------------------------------
    # Test Section 3: integrate.py Edge-Case Functions Stress-Testing
    # ------------------------------------------------------------------
    print("\n--- Test 3: integrate.py Sub-functions Edge-Case Stress-Testing ---")
    edge_symbols = [
        "LOC102723847",
        "105378790",
        "LINC01914",
        "NONEXISTENT_GENE_XYZ999",
        "",
        "   ",
        None,
        12345,
        123.456,
        float('nan'),
    ]

    for sym in edge_symbols:
        # UniProt
        up = get_uniprot_data(sym)
        assert up is None or isinstance(up, dict)

        # STRING single
        st = get_string_data(sym)
        assert isinstance(st, dict)
        assert "partners" in st and isinstance(st["partners"], list)

        # Ensembl
        ens = get_ensembl_data(sym)
        assert isinstance(ens, dict)
        assert "location" in ens

        # ClinVar
        cv = get_clinvar_data(sym)
        assert isinstance(cv, dict)
        assert "status" in cv

        # GTEx eQTLs
        eqtls = get_gtex_eqtls(sym)
        assert isinstance(eqtls, list)

    # KEGG & PDB & AlphaFold with edge identifiers
    edge_ids = [None, "", "   ", "INVALID_ID_999", 12345, float('nan')]
    for eid in edge_ids:
        kg = get_kegg_data(eid)
        assert isinstance(kg, dict)
        assert "pathways" in kg and isinstance(kg["pathways"], list)

        pdb = get_pdb_data(eid)
        assert pdb is None or isinstance(pdb, dict)

        af = get_alphafold_data(eid)
        assert af is None or isinstance(af, str)

        ot_drugs, ot_ess = get_opentargets_data(eid)
        assert isinstance(ot_drugs, list)
        assert isinstance(ot_ess, bool)

        tcga = get_tcga_survival(eid)
        assert isinstance(tcga, bool)

    # Enrichr TFs with edge lists
    edge_tf_lists = [
        [],
        None,
        ["LOC102723847", "105378790", "LINC01914"],
        ["", "   ", None, "nan", float('nan'), 12345],
        ["NONEXISTENT_GENE_XYZ999"]
    ]
    for tfl in edge_tf_lists:
        tfs = get_enrichr_tfs(tfl)
        assert isinstance(tfs, list)

    # STRING PPI with edge lists
    edge_ppi_lists = [
        [],
        None,
        [{"symbol": "LOC102723847"}, {"symbol": "105378790"}, {"symbol": "LINC01914"}],
        [{"symbol": ""}, {"symbol": None}, {"symbol": float('nan')}, {"symbol": 12345}],
    ]
    for ppl in edge_ppi_lists:
        ppi = get_string_ppi(ppl)
        assert isinstance(ppi, list)

    print("PASS: All integrate.py individual sub-functions handled edge cases cleanly.")

    # ------------------------------------------------------------------
    # Test Section 4: run_integration End-to-End Stress Test
    # ------------------------------------------------------------------
    print("\n--- Test 4: run_integration End-to-End Stress Test ---")
    stress_deg_list = [
        {"symbol": "LOC102723847", "log2fc": -1.5, "padj": 0.02, "baseMean": 80.0},
        {"symbol": "105378790", "log2fc": 2.1, "padj": 0.001, "baseMean": 34.0},
        {"symbol": "LINC01914", "log2fc": None, "padj": None, "baseMean": 120.0},
        {"symbol": "NONEXISTENT_XYZ", "log2fc": 0.0, "padj": 0.5, "baseMean": 10.0},
        {"symbol": "TP53", "log2fc": 3.4, "padj": 1e-6, "baseMean": 4500.0},
        {"symbol": "", "log2fc": 1.0, "padj": 0.1, "baseMean": 5.0},
        {"symbol": 12345, "log2fc": -0.5, "padj": None, "baseMean": None},
    ]

    res = run_integration(stress_deg_list, is_cancer=True)
    assert "results" in res
    assert "master_tfs" in res
    assert "ppi_network" in res

    results = res["results"]
    assert len(results) == len(stress_deg_list), f"Expected {len(stress_deg_list)} results, got {len(results)}"

    # Check preserved symbols
    symbols_out = [r["symbol"] for r in results]
    print(f"run_integration output symbols: {symbols_out}")
    assert "LOC102723847" in symbols_out
    assert "105378790" in symbols_out
    assert "LINC01914" in symbols_out
    assert "TP53" in symbols_out

    # Check that coverage gaps were populated for unannotated genes
    loc_record = next(r for r in results if r["symbol"] == "LOC102723847")
    print(f"LOC102723847 record coverage gaps: {loc_record.get('coverage_gaps')}")
    assert "UniProt Function" in loc_record.get("coverage_gaps", [])

    # Check strict JSON serialization compliance
    dumped = json.dumps(res, allow_nan=False)
    parsed = json.loads(dumped)
    assert len(parsed["results"]) == len(stress_deg_list)
    print("PASS: run_integration end-to-end stress test completed with strict JSON compliance.")
    print("\n======================================================================")
    print("ALL BACKEND EDGE-CASE STRESS TESTS PASSED SUCCESSFULLY!")
    print("======================================================================")

if __name__ == "__main__":
    run_tests()
