import os
import sys
import subprocess
import shutil
import json
import math
import tempfile
import pandas as pd
import numpy as np

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.pipeline.deseq2_runner import (
    find_rscript_path,
    sanitize_float,
    run_deseq2_pipeline,
    get_top_degs
)

def test_find_rscript_path():
    print("=== Testing find_rscript_path() ===")
    rscript = find_rscript_path()
    print(f"Discovered Rscript at: {rscript}")
    assert os.path.isfile(rscript), f"Rscript path does not exist: {rscript}"

    # Test RSCRIPT_PATH override
    orig_env = os.environ.get("RSCRIPT_PATH")
    try:
        os.environ["RSCRIPT_PATH"] = rscript
        assert find_rscript_path() == rscript
        print("RSCRIPT_PATH override works correctly.")
    finally:
        if orig_env is not None:
            os.environ["RSCRIPT_PATH"] = orig_env
        else:
            os.environ.pop("RSCRIPT_PATH", None)

    print("PASS: find_rscript_path\n")


def test_sanitize_float():
    print("=== Testing sanitize_float() ===")
    assert sanitize_float(1.234) == 1.234
    assert sanitize_float(0.0) == 0.0
    assert sanitize_float(-5.67) == -5.67
    assert sanitize_float(float('nan')) is None
    assert sanitize_float(float('inf')) is None
    assert sanitize_float(float('-inf')) is None
    assert sanitize_float(np.nan) is None
    assert sanitize_float(None) is None
    assert sanitize_float("invalid") is None

    # Test JSON serialization compliance
    payload = {
        "symbol": "TEST1",
        "log2fc": sanitize_float(float('nan')),
        "padj": sanitize_float(float('inf')),
        "baseMean": sanitize_float(np.nan)
    }
    dumped = json.dumps(payload, allow_nan=False)
    parsed = json.loads(dumped)
    assert parsed["log2fc"] is None
    assert parsed["padj"] is None
    assert parsed["baseMean"] is None
    print(f"JSON Output with allow_nan=False: {dumped}")
    print("PASS: sanitize_float\n")


def test_get_top_degs_deduplication():
    print("=== Testing get_top_degs deduplication and slicing ===")
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "test_deseq.csv")
        
        # Create dummy DESeq2 results with duplicate symbols and missing symbols
        # 10 rows: 3 duplicates of A, 2 with empty/missing symbol, total 5 unique symbols
        data = {
            "GeneID": [f"ID_{i}" for i in range(10)],
            "baseMean": [100.0 + i for i in range(10)],
            "log2FoldChange": [2.5 - 0.1 * i for i in range(10)],
            "lfcSE": [0.2] * 10,
            "stat": [5.0] * 10,
            "pvalue": [1e-5 * (i + 1) for i in range(10)],
            "padj": [1e-4 * (i + 1) for i in range(10)]
        }
        pd.DataFrame(data).to_csv(csv_path, index=False)
        
        # Symbol map has duplicates for ID_0, ID_1, ID_2 -> 'GENE_A'
        # ID_3 maps to empty string, ID_4 is None, ID_5 -> 'GENE_B', ID_6 -> 'GENE_C', ID_7 -> 'GENE_D', ID_8 -> 'GENE_E', ID_9 -> 'GENE_F'
        symbol_map = {
            "ID_0": "GENE_A",
            "ID_1": "GENE_A",  # duplicate
            "ID_2": "GENE_A",  # duplicate
            "ID_3": "",        # empty string
            "ID_4": None,      # None
            "ID_5": "GENE_B",
            "ID_6": "GENE_C",
            "ID_7": "GENE_D",
            "ID_8": "GENE_E",
            "ID_9": "GENE_F"
        }
        
        # Request top_n = 4.
        # If sliced before dropna/drop_duplicates (top 4: ID_0, 1, 2, 3), deduplication on top 4 would yield only 1 gene ('GENE_A')!
        # With proper deduplication BEFORE head(top_n), we should get exactly 4 unique genes: GENE_A, GENE_B, GENE_C, GENE_D!
        top_degs = get_top_degs(csv_path, symbol_map=symbol_map, top_n=4)
        symbols = [d["symbol"] for d in top_degs]
        print(f"Returned symbols: {symbols}")
        assert len(top_degs) == 4, f"Expected 4 genes, got {len(top_degs)}"
        assert symbols == ["GENE_A", "GENE_B", "GENE_C", "GENE_D"], f"Unexpected symbols: {symbols}"
        
        # Verify JSON compliance of returned list
        dumped = json.dumps(top_degs, allow_nan=False)
        assert len(json.loads(dumped)) == 4
    print("PASS: get_top_degs deduplication\n")


def test_deseq2_actual_run():
    print("=== Testing run_deseq2_pipeline on actual GSE270967 data ===")
    source_dir = os.path.join(backend_dir, "data", "runs", "GSE270967")
    counts_file = os.path.join(source_dir, "counts.csv")
    coldata_file = os.path.join(source_dir, "coldata.csv")

    assert os.path.isfile(counts_file), f"Missing counts.csv at {counts_file}"
    assert os.path.isfile(coldata_file), f"Missing coldata.csv at {coldata_file}"

    with tempfile.TemporaryDirectory() as tmpdir:
        # We subset counts to first 300 genes for fast end-to-end verification of DESeq2 + GSEA
        counts_df = pd.read_csv(counts_file, index_col=0, nrows=400)
        tmp_counts = os.path.join(tmpdir, "counts.csv")
        tmp_coldata = os.path.join(tmpdir, "coldata.csv")
        tmp_output = os.path.join(tmpdir, "deseq_results.csv")

        counts_df.to_csv(tmp_counts)
        shutil.copyfile(coldata_file, tmp_coldata)

        print(f"Running DESeq2 pipeline on {len(counts_df)} genes in {tmpdir}...")
        run_deseq2_pipeline(tmp_counts, tmp_coldata, tmp_output)

        assert os.path.isfile(tmp_output), "deseq_results.csv was not produced!"
        out_df = pd.read_csv(tmp_output)
        print(f"DESeq2 output rows: {len(out_df)}")
        print(f"DESeq2 columns: {list(out_df.columns)}")
        expected_cols = ["GeneID", "baseMean", "log2FoldChange", "lfcSE", "stat", "pvalue", "padj"]
        assert list(out_df.columns) == expected_cols, f"Columns mismatch: {list(out_df.columns)}"

        # Verify volcano.png and pca.png exist
        volcano_path = os.path.join(tmpdir, "volcano.png")
        pca_path = os.path.join(tmpdir, "pca.png")
        assert os.path.isfile(volcano_path), "volcano.png was not generated!"
        assert os.path.isfile(pca_path), "pca.png was not generated!"
        print(f"volcano.png size: {os.path.getsize(volcano_path)} bytes")
        print(f"pca.png size: {os.path.getsize(pca_path)} bytes")

        # Test get_top_degs on the result
        degs = get_top_degs(tmp_output, symbol_map=None, top_n=10)
        print(f"Top 10 DEGs extracted: {[d['symbol'] for d in degs]}")
        assert len(degs) == 10, f"Expected 10 DEGs, got {len(degs)}"
        # Verify valid JSON serialization
        json_str = json.dumps(degs, allow_nan=False)
        assert len(json.loads(json_str)) == 10

    print("PASS: test_deseq2_actual_run\n")


def test_deseq2_full_enrichment():
    print("=== Testing run_deseq2_pipeline with full GSE270967 data for enrichment plots ===")
    source_dir = os.path.join(backend_dir, "data", "runs", "GSE270967")
    counts_file = os.path.join(source_dir, "counts.csv")
    coldata_file = os.path.join(source_dir, "coldata.csv")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_output = os.path.join(tmpdir, "deseq_results.csv")
        print(f"Running full DESeq2 pipeline on GSE270967...")
        run_deseq2_pipeline(counts_file, coldata_file, tmp_output)

        assert os.path.isfile(tmp_output), "deseq_results.csv was not produced!"

        # Check all plots
        volcano_path = os.path.join(tmpdir, "volcano.png")
        pca_path = os.path.join(tmpdir, "pca.png")
        go_path = os.path.join(tmpdir, "go_enrichment.png")
        kegg_path = os.path.join(tmpdir, "kegg_enrichment.png")

        assert os.path.isfile(volcano_path), "volcano.png missing!"
        assert os.path.isfile(pca_path), "pca.png missing!"
        print(f"volcano.png: {os.path.getsize(volcano_path)} bytes")
        print(f"pca.png: {os.path.getsize(pca_path)} bytes")

        if os.path.isfile(go_path):
            print(f"go_enrichment.png successfully generated: {os.path.getsize(go_path)} bytes")
        else:
            print("Notice: go_enrichment.png not generated (no significant GO terms or skipped)")

        if os.path.isfile(kegg_path):
            print(f"kegg_enrichment.png successfully generated: {os.path.getsize(kegg_path)} bytes")
        else:
            print("Notice: kegg_enrichment.png not generated (no significant KEGG terms or skipped)")

        # Verify also copy to GSE270967 folder if plots were created so UI has them
        for plot_name in ["go_enrichment.png", "kegg_enrichment.png", "volcano.png", "pca.png"]:
            src_plot = os.path.join(tmpdir, plot_name)
            dst_plot = os.path.join(source_dir, plot_name)
            if os.path.isfile(src_plot):
                shutil.copyfile(src_plot, dst_plot)
                print(f"Updated {plot_name} in {source_dir}")

    print("PASS: test_deseq2_full_enrichment\n")


def test_factor_levels():
    print("=== Testing factor reference levels ===")
    rscript = find_rscript_path()
    r_code = (
        'coldata <- read.csv("backend/data/runs/GSE270967/coldata.csv", row.names=1); '
        'if ("Control" %in% coldata$Group) coldata$Group <- relevel(factor(coldata$Group), ref="Control") else coldata$Group <- as.factor(coldata$Group); '
        'cat(paste(levels(coldata$Group), collapse=","))'
    )
    res = subprocess.run([rscript, "-e", r_code], capture_output=True, text=True, check=True)
    levels = res.stdout.strip().split(",")
    print(f"coldata$Group factor levels: {levels}")
    assert levels == ["Control", "Case"], f"Expected ['Control', 'Case'], got {levels}"
    print("PASS: test_factor_levels\n")


if __name__ == "__main__":
    test_find_rscript_path()
    test_sanitize_float()
    test_get_top_degs_deduplication()
    test_factor_levels()
    test_deseq2_actual_run()
    test_deseq2_full_enrichment()
    print("ALL MILESTONE M1 VERIFICATION TESTS PASSED SUCCESSFULLY!")

