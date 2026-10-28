import subprocess
import os
import shutil
import glob
import math
from typing import Dict, Any, List, Optional
import pandas as pd


def find_rscript_path() -> str:
    """
    Dynamically locates the Rscript executable:
    1. os.environ.get("RSCRIPT_PATH")
    2. shutil.which("Rscript")
    3. Windows common paths (e.g. C:\Program Files\R\R-*\bin\Rscript.exe, C:\Program Files\R\R-4.5.3\bin\Rscript.exe)
    4. Linux/Unix common paths (/usr/bin/Rscript, /usr/local/bin/Rscript)
    Raises RuntimeError if Rscript executable is not found.
    """
    # 1. Environment variable
    env_path = os.environ.get("RSCRIPT_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 2. System PATH
    which_path = shutil.which("Rscript")
    if which_path:
        return which_path

    # 3. Known fallback paths
    candidate_paths = [
        r"C:\Program Files\R\R-4.5.3\bin\Rscript.exe",
        r"C:\Program Files\R\R-4.5.3\bin\x64\Rscript.exe",
        "/usr/bin/Rscript",
        "/usr/local/bin/Rscript",
    ]
    for p in candidate_paths:
        if os.path.isfile(p):
            return p

    # Search wildcard matches across R versions on Windows
    wildcard_matches = sorted(glob.glob(r"C:\Program Files\R\R-*\bin\Rscript.exe"), reverse=True)
    if wildcard_matches:
        return wildcard_matches[0]

    raise RuntimeError(
        "Rscript executable not found. Please ensure R is installed and added to PATH, "
        "or set the RSCRIPT_PATH environment variable."
    )


def sanitize_float(val: Any) -> Optional[float]:
    """
    Ensures float values are finite and JSON-compliant.
    NaN, +Inf, -Inf, and invalid numbers are converted to None (JSON null).
    """
    if val is None or pd.isna(val):
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (ValueError, TypeError):
        return None


def run_deseq2_pipeline(counts_csv: str, coldata_csv: str, output_csv: str):
    """
    Invokes the run_deseq2.R script via subprocess using dynamically located Rscript.
    """
    rscript_bin = find_rscript_path()
    r_script = os.path.join(os.path.dirname(__file__), "run_deseq2.R")

    cmd = [
        rscript_bin,
        r_script,
        counts_csv,
        coldata_csv,
        output_csv
    ]

    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("DESeq2 Output:", result.stdout)
    except subprocess.CalledProcessError as e:
        print("DESeq2 Error:", e.stderr)
        raise RuntimeError(f"DESeq2 failed: {e.stderr}")


def get_top_degs(deseq_output_csv: str, symbol_map: Optional[dict] = None, top_n: int = 15) -> List[Dict[str, Any]]:
    """
    Reads the DESeq2 output, maps IDs to gene symbols, filters NA/duplicates
    BEFORE selecting top_n, and returns JSON-sanitized top N DEGs.
    """
    df = pd.read_csv(deseq_output_csv)

    # Ensure ordered by padj (with NA padj placed at the end)
    df = df.sort_values('padj', na_position='last')

    if symbol_map:
        # Map IDs to gene symbols
        df['Symbol'] = df['GeneID'].astype(str).map(symbol_map)
        df = df.dropna(subset=['Symbol'])
        df = df[df['Symbol'].astype(str).str.strip() != ""]
        df = df.drop_duplicates(subset=['Symbol'])
        top_genes = df.head(top_n).copy()
    else:
        # If no symbol map provided, translate candidate IDs via MyGene if numeric/Ensembl
        # Use an expanded pool so deduplication and dropna leave at least top_n items
        pool_size = min(len(df), max(top_n * 4, 100))
        candidates = df.head(pool_size).copy()
        ids_to_map = candidates['GeneID'].astype(str).tolist()

        needs_mapping = any(x.isdigit() or x.startswith("ENSG") for x in ids_to_map[:10])
        if needs_mapping and len(ids_to_map) > 0:
            try:
                import requests
                res = requests.post(
                    'https://mygene.info/v3/query',
                    data={'q': ','.join(ids_to_map), 'scopes': 'entrezgene,ensemblgene', 'fields': 'symbol', 'species': 'human'},
                    timeout=15
                )
                if res.status_code == 200:
                    mapped = res.json()
                    id_to_sym = {item['query']: item.get('symbol', item['query']) for item in mapped if 'query' in item and item.get('symbol')}
                    candidates['Symbol'] = candidates['GeneID'].astype(str).map(lambda x: id_to_sym.get(x, x))
                else:
                    candidates['Symbol'] = candidates['GeneID'].astype(str)
            except Exception as e:
                print(f"MyGene mapping failed: {e}")
                candidates['Symbol'] = candidates['GeneID'].astype(str)
        else:
            candidates['Symbol'] = candidates['GeneID'].astype(str)

        candidates = candidates.dropna(subset=['Symbol'])
        candidates = candidates[candidates['Symbol'].astype(str).str.strip() != ""]
        candidates = candidates.drop_duplicates(subset=['Symbol'])

        # If pool_size wasn't enough to yield top_n genes and df has more rows, expand pool
        if len(candidates) < top_n and len(df) > pool_size:
            larger_pool_size = min(len(df), max(top_n * 8, 300))
            candidates = df.head(larger_pool_size).copy()
            ids_to_map = candidates['GeneID'].astype(str).tolist()
            if needs_mapping and len(ids_to_map) > 0:
                try:
                    import requests
                    res = requests.post(
                        'https://mygene.info/v3/query',
                        data={'q': ','.join(ids_to_map), 'scopes': 'entrezgene,ensemblgene', 'fields': 'symbol', 'species': 'human'},
                        timeout=20
                    )
                    if res.status_code == 200:
                        mapped = res.json()
                        id_to_sym = {item['query']: item.get('symbol', item['query']) for item in mapped if 'query' in item and item.get('symbol')}
                        candidates['Symbol'] = candidates['GeneID'].astype(str).map(lambda x: id_to_sym.get(x, x))
                    else:
                        candidates['Symbol'] = candidates['GeneID'].astype(str)
                except Exception as e:
                    print(f"MyGene mapping failed: {e}")
                    candidates['Symbol'] = candidates['GeneID'].astype(str)
            else:
                candidates['Symbol'] = candidates['GeneID'].astype(str)

            candidates = candidates.dropna(subset=['Symbol'])
            candidates = candidates[candidates['Symbol'].astype(str).str.strip() != ""]
            candidates = candidates.drop_duplicates(subset=['Symbol'])

        top_genes = candidates.head(top_n).copy()

    deg_list = []
    for _, row in top_genes.iterrows():
        deg_list.append({
            "symbol": str(row['Symbol']),
            "log2fc": sanitize_float(row.get('log2FoldChange')),
            "padj": sanitize_float(row.get('padj')),
            "baseMean": sanitize_float(row.get('baseMean')),
        })

    return deg_list
