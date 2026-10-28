# OmniGeneDB: Scientific Architecture & Bioinformatics Framework

This document outlines the biological methodologies, statistical models, and systemic constraints of the OmniGeneDB platform, written for computational biologists and bioinformaticians.

---

## 1. Transcriptomic Ingestion & Normalization
OmniGeneDB automates the transition from raw sequencing data to statistical modeling, but imposes strict biological and mathematical constraints to ensure data integrity.

### 1.1 Modality Constraints (The Microarray Guardrail)
*   **Feature:** The system automatically scrapes NCBI GEO metadata (`!Series_type` and `!Series_platform_id`) to identify the sequencing modality.
*   **Constraint:** OmniGeneDB **strictly rejects Microarray datasets** (e.g., Affymetrix, Illumina BeadChip). 
*   **Bioinformatics Rationale:** The core statistical engine (DESeq2) explicitly requires un-normalized, raw integer count data because it utilizes a Negative Binomial generalized linear model to estimate mean-variance relationships. Microarray data consists of continuous fluorescence intensity values (often log2-transformed or RMA-normalized), which violate the core assumptions of the Negative Binomial distribution and will cause the R runtime to fatally crash or produce mathematically invalid p-values.

### 1.2 Data Acquisition
*   **Feature:** For valid RNA-Seq datasets, the platform prioritizes downloading the NCBI-standardized `raw_counts_GRCh38.p13_NCBI.tsv.gz` matrix.
*   **Constraint:** If NCBI GEO has not precomputed this specific track (which occasionally happens, resulting in a HTTP 404), the pipeline falls back to `GEOparse` to attempt parsing the user-submitted supplementary matrix. However, if the supplementary matrix is pre-normalized (e.g., FPKM, TPM, CPM), DESeq2's internal size-factor estimation will be compromised.

---

## 2. Statistical Core (DESeq2)
*   **Methodology:** The system invokes an embedded R 4.3 runtime to execute the Bioconductor `DESeq2` package.
*   **Design Formula:** It utilizes a standard `~ Group` design matrix (Case vs. Control).
*   **Output Metrics:** Calculates `log2FoldChange` (effect size), `baseMean` (average expression), and `padj` (Benjamini-Hochberg False Discovery Rate for multiple testing correction).
*   **Filtration Constraint:** The Python backend dynamically parses the output CSV, filtering out genes with `padj = NA` (which DESeq2 flags due to extreme count outliers or low mean normalized counts via independent filtering). It strictly sorts by `padj` to prioritize the most statistically significant hits for downstream API enrichment.

---

## 3. Systems Biology & Pathway Analysis
Rather than analyzing genes in isolation, the pipeline maps differential expression vectors into functional biological spaces.

### 3.1 Immune Deconvolution (MCPcounter)
*   **Methodology:** Uses the `MCPcounter` algorithm (Microenvironment Cell Populations-counter) inside R.
*   **Biological Mechanism:** It quantifies the absolute abundance of 8 immune and 2 stromal cell populations in heterogeneous tissues by leveraging highly specific transcriptomic marker genes.
*   **Constraint:** This is most biologically valid for bulk tissue samples (especially solid tumors). If the input dataset is already an isolated cell line (e.g., *A549* or *HeLa*), the deconvolution will predictably (and correctly) return near-zero for immune fractions like CD8+ T-cells.

### 3.2 Gene Set Enrichment Analysis (GSEA)
*   **Methodology:** Utilizes `clusterProfiler` for hyper-geometric enrichment testing of up/down-regulated gene clusters against the **Gene Ontology (GO)** (Biological Processes) and **KEGG** pathway databases.
*   **Constraint:** Requires mapping to the human genome annotation database (`org.Hs.eg.db`). If a user inputs a non-human dataset (e.g., mouse or drosophila) without proper ortholog mapping, the `clusterProfiler` step will yield empty pathway results.

### 3.3 Transcription Factor Network (Enrichr / ChEA)
*   **Methodology:** Queries the Ma'ayan Lab Enrichr API (specifically the ChEA 2022 database) to identify Master Transcription Factors whose known downstream regulatory targets are statistically overrepresented in the top DEG list.

---

## 4. Multi-Omics Integrations (The Top DEG Table)
OmniGeneDB's defining feature is its ability to instantly link a transcriptomic p-value to external genomic, pharmacological, and structural databases.

### 4.1 Pharmacology & Oncology (OpenTargets)
*   **Drugs:** Queries the OpenTargets GraphQL API via Ensembl IDs to fetch known clinical drugs and clinical candidates.
*   **DepMap Essentiality (🔥 ESSENTIAL):** Checks Broad Institute CRISPR-Cas9 knockout screens. Flags genes that are structurally required for cell survival (vital for assessing drug toxicity vs. tumor vulnerability).
*   **TCGA Prognostic (🎗️ CANCER PROGNOSTIC):** *Conditional Feature.* If the "Cancer" checkbox is toggled, it checks if the gene is flagged in the Cancer Hallmarks database or linked to patient survival curves in The Cancer Genome Atlas.

### 4.2 Structural Biology
*   **AlphaFold & PDB:** Maps the UniProt/Ensembl ID to the RCSB Protein Data Bank (fetching experimental crystallography/Cryo-EM structures) or AlphaFold 3D (for highly accurate computational predictions), rendering direct deep-links to 3D viewers.

### 4.3 Genetics & Pathology (GTEx & ClinVar)
*   **ClinVar:** Queries the NCBI E-utilities to count the number of known "Pathogenic" or "Likely Pathogenic" Mendelian variants associated with the gene.
*   **GTEx (eQTLs):** Scrapes the Genotype-Tissue Expression database to identify if non-coding genomic variants (SNPs) significantly alter the expression of this gene across 54 human tissues, linking GWAS genetics to the transcriptomic output.

### 4.4 Protein-Protein Interactions (STRING-DB)
*   **Methodology:** Queries the STRING database REST API with the list of top DEGs to fetch experimental and predicted physical/functional protein interactions (Species: 9606 / Human).
*   **Visualization:** Renders an interactive, physics-based force-directed graph (`react-force-graph-2d`) in the React frontend, allowing researchers to visualize the topology of the perturbed biological network.
