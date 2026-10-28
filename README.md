# OmniGeneDB

> **Multi-Database Integration and Functional Profiling of Disease-Associated Gene Networks**

[![Live Cloud Demo](https://img.shields.io/badge/Live%20Demo-Google%20Cloud%20Run-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white)](https://omnigenedb-frontend-vfhgxd7ida-uc.a.run.app)
[![Frontend](https://img.shields.io/badge/Frontend-React%2019%20%7C%20Vite%20%7C%20Tailwind-61DAFB?style=flat-square&logo=react&logoColor=black)](frontend/)
[![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.11-009688?style=flat-square&logo=fastapi&logoColor=white)](backend/)
[![Statistical Core](https://img.shields.io/badge/Bioconductor-DESeq2%20%7C%20MCPcounter%20%7C%20clusterProfiler-1E88E5?style=flat-square&logo=r&logoColor=white)](backend/app/pipeline/)
[![Cloud Architecture](https://img.shields.io/badge/Deployment-Cloud%20Run%20%2B%20GCS%20FUSE-FF6F00?style=flat-square&logo=googlecloud&logoColor=white)](DEPLOY.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](LICENSE)

---

## 🌐 Live Cloud Deployment

OmniGeneDB is live and fully accessible on **Google Cloud Run**:

* **🚀 Interactive Web Application:** [https://omnigenedb-frontend-vfhgxd7ida-uc.a.run.app](https://omnigenedb-frontend-vfhgxd7ida-uc.a.run.app)
* **⚡ Backend API Endpoints:** [https://omnigenedb-backend-vfhgxd7ida-uc.a.run.app](https://omnigenedb-backend-vfhgxd7ida-uc.a.run.app)
* **💾 Storage Architecture:** Serverless dual-container architecture backed by Google Cloud Storage FUSE persistent mount for zero-recompute run rehydration.

---

## 🔬 Scientific Overview

**OmniGeneDB** is an automated, cloud-native bioinformatics and systems biology platform that bridges the **Translational Chasm** between raw transcriptomic experiments and actionable clinical pharmacology. 

In conventional workflows, moving from a public NCBI GEO accession to statistical differential expression, immune infiltration estimates, and multi-database target prioritization takes days of custom R/Python scripting and manual database lookups. OmniGeneDB automates this entire pipeline into an autonomous, browser-based workflow running in **under two minutes**.

```
[NCBI GEO Accession]
         │
         ▼
[Automated Factor Detection & Modality Guardrails]
         │
         ▼
[Bioconductor Core: DESeq2 + MCPcounter + clusterProfiler]
         │
         ▼
[Asynchronous Multi-Omics Federation (9 APIs)]
 ├── OpenTargets (Approved Drugs & Active Clinical Trials)
 ├── Broad Institute DepMap (CRISPR Essentiality Screens)
 ├── TCGA Hallmarks (Prognostic Survival Associations)
 ├── GTEx Portal v2 (Tissue-Specific eQTL Variants)
 ├── NCBI ClinVar (Pathogenic Mendelian Mutations)
 ├── UniProt & RCSB PDB / AlphaFold 3D (Catalysis & Structures)
 └── STRING Database (Physics-Based 2D Interactome Network)
         │
         ▼
[Interactive React 19 Translational Dashboard]
```

---

## 🌟 Key Platform Features

### 1. Autonomous Ingestion & Biological Guardrails
* **Automated Factor Discovery:** Ingests any human RNA-seq accession from NCBI GEO. Automatically scrapes the Series Matrix metadata to identify experimental variables (e.g., treatment groups, cell types, dosages, disease states).
* **Microarray Guardrail:** Actively intercepts continuous fluorescence microarray platforms (e.g., Affymetrix, Illumina BeadChip) to prevent mathematical corruption of DESeq2's discrete Negative Binomial model.
* **Standardized GRCh38 Pipeline:** Streams standardized raw count tracks directly from NCBI FTP servers without requiring manual file uploads or FASTQ realignment.

### 2. Bioconductor Statistical Core (R 4.3)
* **DESeq2 Engine:** Automatically normalizes raw library read counts using median-of-ratios size factors, estimates dispersion trends with Empirical Bayes shrinkage, and executes Wald significance testing.
* **Immune & Stromal Deconvolution:** Employs the **`MCPcounter`** algorithm to quantify absolute abundance across 8 immune populations (CD8+ T-cells, NK cells, Monocytes, etc.) and 2 stromal populations (Endothelial cells and Fibroblasts).
* **Gene Set Enrichment (GSEA):** Leverages **`clusterProfiler`** and `org.Hs.eg.db` to calculate hyper-geometric over-representation for **Gene Ontology (GO)** Biological Processes and **KEGG** pathways.
* **Master Transcription Factors:** Queries the Ma'ayan Lab **Enrichr / ChEA** database to infer upstream master regulatory transcription factors whose downstream regulons are significantly perturbed.

### 3. Multi-Omics Target Discovery Layer
The top statistically significant differentially expressed genes ($p_{adj} < 0.05$) are enriched asynchronously across global biomedical knowledgebases:

| Feature Badge / Module | Source Database | Biological & Clinical Significance |
| :--- | :--- | :--- |
| **`Known Drugs`** | **OpenTargets Platform** | Identifies FDA-approved drugs and investigational candidates in active Phase I–IV clinical trials targeting the perturbed gene. |
| **`🔥 ESSENTIAL`** | **Broad DepMap** | Screens genome-wide CRISPR-Cas9 knockout loss-of-fitness data. Identifies genes critical for cell survival across hundreds of cancer cell lines. |
| **`🎗️ CANCER PROGNOSTIC`** | **TCGA Hallmarks** | Flags genes with statistically verified prognostic patient survival correlations across The Cancer Genome Atlas. |
| **`eQTLs (GTEx)`** | **GTEx Portal v2** | Resolves non-coding regulatory SNPs that alter gene expression across 54 non-diseased human tissues, bridging GWAS loci with RNA-seq expression. |
| **`ClinVar Variants`** | **NCBI ClinVar** | Live count and classification of known human Pathogenic and Likely Pathogenic disease-associated genetic mutations. |
| **`3D Structure`** | **PDB & AlphaFold** | Direct deep-links to high-resolution experimental crystal structures (RCSB PDB) and DeepMind AlphaFold predicted 3D conformations. |
| **`Interactome Graph`** | **STRING Database** | Live 2D physics-based force-directed network (`react-force-graph-2d`) illustrating functional protein-protein interaction hubs. |

---

## 🧪 Verified Demonstration Datasets

OmniGeneDB has been benchmarked and verified across multiple biological domains on Google Cloud Run:

| Accession | Biological Disease Domain | Case Group | Control Group | Cancer Flag | Key Biological Findings |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **`GSE153310`** | **Autoimmune / Rheumatic** | `ankylosing spondylitis` | `healthy` | Off | 3 vs 3 balanced design; MSC transcriptomic remodeling in chronic arthritis. |
| **`GSE270967`** | **Oncology (Breast Cancer)** | `responder (pcr)` | `non-responder (rd)` | **On** | Chemotherapy response signatures; identifies `ERBB4` with `🎗️ CANCER PROGNOSTIC` and `🔥 ESSENTIAL` badges. |
| **`GSE147507`** | **Infectious Disease (COVID-19)**| `sars-cov-2 infected (moi 2)` | `mock treatment` | Off | Massive interferon and cytokine storm activation; MCPcounter reveals cell-line baseline. |
| **`GSE136666`** | **Neurodegeneration** | `parkinson's disease` | `control` | Off | Dopaminergic pathway deregulation and post-mortem putamen eQTL identification. |
| **`GSE259421`** | **Aerospace Physiology** | `38 days microgravity` | `ground control` | Off | Deep-space transcriptomic adaptation, DNA repair, and mitochondrial stress responses. |
| **`GSE255359`** | **Pharmacology** | `bevacizumab` | `none` | **On** | Anti-VEGF monoclonal antibody response and angiogenesis inhibition network. |

---

## 📂 Project Structure

```
OmniGeneDB/
├── backend/                       # Python FastAPI & R Bioconductor Service
│   ├── app/
│   │   ├── main.py                # REST API routes & background job orchestrator
│   │   ├── db.py                  # SQLite database engine & schema definitions
│   │   └── pipeline/
│   │       ├── fetch_geo.py       # GEO accession scraper, counts downloader & guardrails
│   │       ├── deseq2_runner.py   # Python-to-R subprocess pipeline bridge
│   │       ├── run_deseq2.R       # Bioconductor DESeq2 + MCPcounter + GSEA script
│   │       └── integrate.py       # Asynchronous Multi-Omics API federation engine
│   ├── tests/                     # Automated backend verification test suite
│   ├── Dockerfile                 # Debian container with R 4.3 + Python 3.11 + Bioconductor
│   ├── docker-entrypoint.sh       # Volume initialization & startup script
│   └── requirements.txt           # Python dependencies
│
├── frontend/                      # React 19 + TypeScript User Interface
│   ├── src/
│   │   ├── components/            # Interactive UI modules, DEG table, and PPI network
│   │   └── App.tsx                # Master analysis view, job status polling & charts
│   ├── tests/                     # Frontend automated edge-case verification
│   ├── Dockerfile                 # Multi-stage production build (Node 20 -> Nginx Alpine)
│   ├── nginx.conf.template        # Dynamic Cloud Run environment proxy template
│   └── package.json
│
├── docs/                          # Scientific & Platform Documentation
│   ├── OmniGeneDB_Scientific_Architecture.md # In-depth bioinformatics & statistical models
│   ├── OmniGeneDB_Documentation.docx         # Comprehensive system manual
│   └── generate_doc.py                       # Automated documentation builder
│
├── e2e/                           # End-to-End AI Browser Verification Protocols
│   ├── browser_test_protocol.md   # Local development verification protocol
│   └── prod_browser_protocol.md   # Live Google Cloud Run verification protocol
│
├── scripts/                       # Maintenance & testing utilities
│   ├── test_counts.py             # NCBI count track availability validator
│   └── test_ot.py                 # OpenTargets GraphQL schema verification
│
├── docker-compose.yml             # Local containerized orchestration
├── deploy.bat                     # Automated Windows deployment script for Cloud Run
├── deploy.sh                      # Automated Unix/macOS deployment script for Cloud Run
├── DEPLOY.md                      # Complete Cloud Run + GCS FUSE architectural guide
├── start.bat                      # Instant Windows local launcher
└── README.md
```

---

## 🛠️ Local Development & Setup

### Option 1: Docker Compose (Recommended)
The easiest way to run the full application with the embedded R environment is via Docker Compose:

```bash
# Clone the repository
git clone https://github.com/your-username/OmniGeneDB.git
cd OmniGeneDB

# Build and start both frontend and backend
docker-compose up --build
```
* **Frontend:** [http://localhost:3000](http://localhost:3000)
* **Backend API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2: Native Development Setup

#### Prerequisites
* **Python 3.10+**
* **Node.js 18+** & `npm`
* **R 4.3+** with Bioconductor packages installed:
  ```R
  if (!requireNamespace("BiocManager", quietly = TRUE)) install.packages("BiocManager")
  BiocManager::install(c("DESeq2", "clusterProfiler", "org.Hs.eg.db", "MCPcounter"))
  ```

#### Backend Setup
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Unix/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## ☁️ Google Cloud Deployment

OmniGeneDB is designed natively for **Google Cloud Run** serverless deployment.

```bash
# Windows
deploy.bat

# Unix / macOS
chmod +x deploy.sh
./deploy.sh
```

For complete instructions on configuring Artifact Registry, Cloud Storage FUSE persistent buckets, and service IAM permissions, refer to the [Deployment Guide (DEPLOY.md)](DEPLOY.md).

---

## 📚 Integrated Biological Data Sources

| Platform | Role in OmniGeneDB | Integration Protocol |
| :--- | :--- | :--- |
| **NCBI GEO** | Raw RNA-seq counts and phenotypic metadata | NCBI FTP & Series Matrix Scraper |
| **Ensembl** | Genomic identifier translator & chromosomal coordinates | Ensembl REST API (`rest.ensembl.org`) |
| **OpenTargets** | Approved drugs, clinical trials & target tractability | OpenTargets GraphQL API v4 |
| **Broad DepMap** | Genome-wide CRISPR-Cas9 essentiality screens | OpenTargets Target DepMap Endpoint |
| **TCGA** | Cancer hallmarks and prognostic survival markers | OpenTargets Hallmarks GraphQL API |
| **GTEx Portal** | Tissue-specific *cis*-eQTL non-coding genetic variants | GTEx Portal REST API v2 |
| **NCBI ClinVar** | Pathogenic and likely pathogenic clinical mutations | NCBI E-utilities REST API |
| **STRING DB** | Protein-protein physical and functional interactome | STRING REST API (`string-db.org`) |
| **UniProtKB** | Functional descriptions, catalytic activity & domains | UniProt REST API (`rest.uniprot.org`) |
| **RCSB PDB** | Experimental 3D crystallography & Cryo-EM coordinates | RCSB Search API v2 |
| **AlphaFold DB**| Predicted 3D protein structure conformations | DeepMind AlphaFold Database API |
| **Enrichr / ChEA**| Upstream master transcription factor identification | Ma'ayan Lab Enrichr API |

---

## 📄 License
This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.
