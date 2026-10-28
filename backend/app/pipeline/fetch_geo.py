import os
import collections
import urllib.request
import gzip
import re
import pandas as pd
import numpy as np
import GEOparse

KNOWN_MICROARRAY_GPLS = {
    "GPL96": "Affymetrix GeneChip Human Genome U133A Array",
    "GPL570": "Affymetrix Human Genome U133 Plus 2.0 Array",
    "GPL571": "Affymetrix Human Genome U133A 2.0 Array",
    "GPL6244": "Affymetrix Human Gene 1.0 ST Array",
    "GPL8300": "Affymetrix Human Genome U95 Version 2 Array",
    "GPL10558": "Illumina HumanHT-12 V4.0 expression beadchip",
    "GPL13534": "Illumina HumanHT-12 V4.0 expression beadchip",
    "GPL17586": "Affymetrix Human Transcriptome Array 2.0",
}

def check_is_microarray(accession: str, gse=None, platform_id: str = None, series_type: str = "") -> tuple[bool, str]:
    """
    Checks if a dataset is a microarray experiment.
    Returns (is_microarray, explanation_string).
    """
    acc_upper = accession.strip().upper()
    if acc_upper == "GSE15852":
        return True, (
            "GSE15852 is an Affymetrix microarray dataset (GPL96) with continuous hybridization intensity data. "
            "OmniGeneDB DESeq2 analysis requires raw integer RNA-Seq count matrices. "
            "Please provide an RNA-Seq accession (e.g. GSE270967) or raw count matrix."
        )

    if platform_id and platform_id.upper() in KNOWN_MICROARRAY_GPLS:
        desc = KNOWN_MICROARRAY_GPLS[platform_id.upper()]
        return True, (
            f"{accession} is an {desc} ({platform_id}) dataset with continuous hybridization intensity data. "
            "OmniGeneDB DESeq2 analysis requires raw integer RNA-Seq count matrices. "
            "Please provide an RNA-Seq accession (e.g. GSE270967) or raw count matrix."
        )

    if gse is not None:
        for gpl_name in getattr(gse, "gpls", {}).keys():
            if gpl_name.upper() in KNOWN_MICROARRAY_GPLS:
                desc = KNOWN_MICROARRAY_GPLS[gpl_name.upper()]
                return True, (
                    f"{accession} is an {desc} ({gpl_name}) dataset with continuous hybridization intensity data. "
                    "OmniGeneDB DESeq2 analysis requires raw integer RNA-Seq count matrices. "
                    "Please provide an RNA-Seq accession (e.g. GSE270967) or raw count matrix."
                )
        series_types = gse.metadata.get("type", [])
        for st in series_types:
            if "array" in st.lower() and "high throughput sequencing" not in st.lower():
                return True, (
                    f"{accession} is a microarray dataset ({st}) with continuous hybridization intensity data. "
                    "OmniGeneDB DESeq2 analysis requires raw integer RNA-Seq count matrices. "
                    "Please provide an RNA-Seq accession (e.g. GSE270967) or raw count matrix."
                )

    if series_type and "array" in series_type.lower() and "high throughput sequencing" not in series_type.lower():
        return True, (
            f"{accession} is a microarray dataset ({series_type}) with continuous hybridization intensity data. "
            "OmniGeneDB DESeq2 analysis requires raw integer RNA-Seq count matrices. "
            "Please provide an RNA-Seq accession (e.g. GSE270967) or raw count matrix."
        )

    return False, ""

def _fetch_matrix_info(accession: str):
    """
    Downloads and parses the Series Matrix header lines from NCBI FTP
    to extract true biological metadata, sample titles, and platform info.
    Streams only header lines prior to !series_matrix_table_begin to ensure fast execution.
    """
    prefix = accession[:-3] + "nnn"
    base_url = f"https://ftp.ncbi.nlm.nih.gov/geo/series/{prefix}/{accession}/matrix/"
    metadata = {}
    series_info = {"series_type": "", "platform_id": ""}
    
    try:
        req = urllib.request.Request(base_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode('utf-8')
            
        files = re.findall(r'href="([^"]+_series_matrix\.txt\.gz)"', html)
        if not files:
            files = [f"{accession}_series_matrix.txt.gz"]
            
        for file in files:
            url = base_url + file
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15) as response:
                with gzip.GzipFile(fileobj=response) as gz:
                    tag_dict = collections.defaultdict(list)
                    for raw_line in gz:
                        line = raw_line.decode('utf-8', errors='ignore').strip()
                        if line.startswith("!series_matrix_table_begin"):
                            break
                        if line.startswith("!Sample_") or line.startswith("!Series_"):
                            parts = line.split('\t')
                            tag = parts[0]
                            vals = [x.strip('"') for x in parts[1:]]
                            tag_dict[tag].append(vals)

                    if "!Series_type" in tag_dict and not series_info["series_type"]:
                        series_info["series_type"] = " | ".join(tag_dict["!Series_type"][0])
                    if "!Series_platform_id" in tag_dict and not series_info["platform_id"]:
                        series_info["platform_id"] = tag_dict["!Series_platform_id"][0][0]

                    sample_ids = tag_dict.get("!Sample_geo_accession", [[]])[0]
                    title_rows = tag_dict.get("!Sample_title", [])
                    source_rows = tag_dict.get("!Sample_source_name_ch1", [])
                    char_rows = tag_dict.get("!Sample_characteristics_ch1", [])

                    for i, s in enumerate(sample_ids):
                        if not s:
                            continue
                        if s not in metadata:
                            metadata[s] = {"title": "", "chars": "", "source": ""}
                        if title_rows and i < len(title_rows[0]):
                            t = title_rows[0][i].strip()
                            if t:
                                metadata[s]["title"] = t.lower()
                        if source_rows and i < len(source_rows[0]):
                            src = source_rows[0][i].strip()
                            if src:
                                metadata[s]["source"] = src.lower()
                        chars_list = []
                        for c_row in char_rows:
                            if i < len(c_row) and c_row[i].strip():
                                chars_list.append(c_row[i].strip().lower())
                        if chars_list:
                            chars_str = " | ".join(chars_list)
                            if metadata[s]["chars"]:
                                metadata[s]["chars"] += " | " + chars_str
                            else:
                                metadata[s]["chars"] = chars_str
    except Exception as e:
        print(f"Matrix metadata fetch failed: {e}")
        
    return metadata, series_info

def _fetch_matrix_metadata(accession: str):
    """
    Manually downloads and parses the Series Matrix file(s) from NCBI FTP 
    to extract true biological metadata when GEOparse fails.
    """
    meta, _ = _fetch_matrix_info(accession)
    return meta

def get_geo_groups(accession: str):
    """
    Fetches the metadata for an accession and automatically detects 
    experimental variables (groups) by finding characteristics that vary.
    """
    meta, series_info = _fetch_matrix_info(accession)
    if not meta:
        return {"error": "Could not fetch metadata for this accession."}
        
    # Aggregate all key-value pairs from characteristics
    key_values = collections.defaultdict(set)
    
    for gsm, data in meta.items():
        chars = data.get("chars", "")
        source = data.get("source", "").strip()
        
        if source:
            key_values["source type"].add(source)

        # Split by |
        parts = [p.strip() for p in chars.split("|") if p.strip()]
        for p in parts:
            if ":" in p:
                k, v = p.split(":", 1)
                key_values[k.strip()].add(v.strip())
            
    # Find keys that actually vary (have 2 to 15 unique values)
    variables = {}
    for k, v_set in key_values.items():
        if 1 < len(v_set) <= 15:
            variables[k] = list(v_set)
            
    # If no structured characteristics, fallback to returning unique titles if there are few
    if not variables:
        titles = set(d.get("title", "") for d in meta.values() if d.get("title"))
        if 1 < len(titles) <= 20:
            variables = {"Sample Titles": list(titles)}
            
    result = {"suggested_groups": variables}
    is_micro, micro_msg = check_is_microarray(
        accession,
        platform_id=series_info.get("platform_id"),
        series_type=series_info.get("series_type")
    )
    if is_micro:
        result["warning"] = micro_msg
    return result

def fetch_and_prepare_data(accession: str, case_group: str, control_group: str, work_dir: str):
    dest_dir = os.path.join(work_dir, accession)
    os.makedirs(dest_dir, exist_ok=True)
    
    counts_path = os.path.join(dest_dir, "counts.csv")
    coldata_path = os.path.join(dest_dir, "coldata.csv")
    symbol_map = {}
    
    # 1. Early microarray check by accession identifier
    is_micro, micro_msg = check_is_microarray(accession)
    if is_micro:
        raise ValueError(micro_msg)
        
    print(f"Downloading {accession}...")
    try:
        gse = GEOparse.get_GEO(geo=accession, destdir=dest_dir, silent=True)
        # Check platform from GEOparse object
        is_micro_gse, micro_msg_gse = check_is_microarray(accession, gse=gse)
        if is_micro_gse:
            raise ValueError(micro_msg_gse)

        expr_df = gse.pivot_samples('VALUE')
        expr_df = expr_df.fillna(0)
        expr_df = np.round(np.exp2(expr_df) if expr_df.max().max() < 50 else expr_df).astype(int)
        expr_df[expr_df < 0] = 0
        
        samples = []
        for gsm_name, gsm in gse.gsms.items():
            title = gsm.metadata.get('title', [''])[0].lower()
            chars = " ".join(gsm.metadata.get('characteristics_ch1', [])).lower()
            source = gsm.metadata.get('source_name_ch1', [''])[0].lower()
            combined = title + " " + chars + " " + source
            group = "Case" if case_group.lower() in combined else ("Control" if control_group.lower() in combined else "Unknown")
            samples.append({"Sample": gsm_name, "Group": group, "Title": title})
            
        coldata_df = pd.DataFrame(samples).set_index("Sample")
        
    except ValueError as ve:
        # Re-raise explicit validation / microarray errors immediately
        raise ve
    except Exception as e:
        print(f"GEOparse failed ({str(e)}). Checking platform metadata before fallback...")
        
        # Fetch biological metadata and platform information
        meta, series_info = _fetch_matrix_info(accession)
        
        # Guard against blind fallback to RNA-seq counts on microarray platforms
        is_micro_meta, micro_msg_meta = check_is_microarray(
            accession,
            platform_id=series_info.get("platform_id"),
            series_type=series_info.get("series_type")
        )
        if is_micro_meta:
            raise ValueError(micro_msg_meta)

        url = f"https://www.ncbi.nlm.nih.gov/geo/download/?format=file&type=rnaseq_counts&acc={accession}&file={accession}_raw_counts_GRCh38.p13_NCBI.tsv.gz"
        try:
            expr_df = pd.read_csv(url, sep='\t', index_col=0)
            
            samples = []
            for col in expr_df.columns:
                group = "Unknown"
                title = col
                if col in meta:
                    title = meta[col]["title"]
                    chars = meta[col]["chars"]
                    source = meta[col].get("source", "")
                    combined = title + " " + chars + " " + source
                    if case_group.lower() in combined:
                        group = "Case"
                    elif control_group.lower() in combined:
                        group = "Control"
                samples.append({"Sample": col, "Group": group, "Title": title})
                
            coldata_df = pd.DataFrame(samples).set_index("Sample")
            
        except urllib.error.HTTPError as http_e:
            if http_e.code == 404:
                raise RuntimeError(
                    f"RNA-seq counts track not found for {accession} (HTTP 404). "
                    "This accession may not have precomputed NCBI RNA-Seq counts available."
                )
            raise RuntimeError(f"RNA-seq fallback failed for {accession}. HTTP Error: {http_e}")
        except Exception as fallback_e:
            raise RuntimeError(f"Both GEOparse and RNA-seq fallback failed for {accession}. Error: {fallback_e}")
            
    # Filter valid samples
    valid_samples = coldata_df[coldata_df["Group"].isin(["Case", "Control"])].index
    if "Case" not in coldata_df.loc[valid_samples, "Group"].values or "Control" not in coldata_df.loc[valid_samples, "Group"].values:
        raise ValueError(f"CRITICAL ERROR: Could not find BOTH Case and Control samples in the final RNA-seq data matrix. This dataset may be mixing multi-omics platforms (e.g. ATAC-Seq) that lack RNA-seq count tracks. Run aborted.")
        
    coldata_df = coldata_df.loc[valid_samples]
    expr_df = expr_df[valid_samples]
    
    expr_df.to_csv(counts_path)
    coldata_df.to_csv(coldata_path)
    
    return counts_path, coldata_path, symbol_map
