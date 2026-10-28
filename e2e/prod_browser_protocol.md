# OmniGeneDB Production E2E Testing Protocol (Cloud Run)

This document contains standard operating procedures (SOPs) and prompts for the Antigravity Browser Agent. 
To run these tests, open the chat and type:
`/browser execute all test cases in e2e/prod_browser_protocol.md on https://omnigenedb-frontend-vfhgxd7ida-uc.a.run.app`

---

## Prerequisites
Before starting, ensure that:
1. The target URL is the live Google Cloud Run deployment: `https://omnigenedb-frontend-vfhgxd7ida-uc.a.run.app`
2. Wait times for the DESeq2 pipeline may take up to 4-5 minutes on the cloud depending on cold starts.

---

## Test Case 1: The Happy Path (Cloud RNA-Seq Pipeline)
**Objective**: Verify that a valid RNA-seq dataset successfully completes the entire pipeline on the cloud and renders basic visuals.

**Browser Agent Instructions**:
1. Navigate to `https://omnigenedb-frontend-vfhgxd7ida-uc.a.run.app`.
2. Locate the "Submit Run" or "New Analysis" form.
3. In the "GEO Accession" input field, type `GSE270967`.
4. Click outside the input box to trigger the metadata scanner.
5. Enter `non-responder (rd)` into the **Case Group** input.
6. Enter `responder (pcr)` into the **Control Group** input.
7. Ensure the "Is this a Cancer/Oncology dataset?" checkbox is **checked**.
8. Click "Submit" or "Run Pipeline".
9. **Wait** for the pipeline to finish (this may take up to 5 minutes on Cloud Run).
10. **Assertions**: Once the results page loads, verify:
    - A "Volcano (Significance)" plot canvas/image.
    - A "PCA (Variance)" plot canvas/image.
    - A "Master Transcription Factors" card containing text.

---

## Test Case 2: Advanced Biological Modules
**Objective**: Verify that the new Phase 4 systems biology modules render correctly.

**Browser Agent Instructions**:
1. Scroll down the `GSE270967` results page.
2. **Assertions**:
    - Assert the presence of an "Immune Deconvolution" or immune cell fractions chart.
    - Assert the presence of a "STRING PPI Network" graph or interactive canvas.
    - Assert the presence of "Gene Ontology" and "KEGG" enrichment visuals or tables.

---

## Test Case 3: DEG Table External Integrations
**Objective**: Verify that the Python multi-omics API integrations successfully populated the frontend table.

**Browser Agent Instructions**:
1. Locate the "Top Differentially Expressed Genes" data table.
2. **Assertions**:
    - Verify the "Known Drugs (OpenTargets)" column contains text/drug names.
    - Verify the "eQTLs" column contains text (GTEx variants).
    - Verify the "ClinVar" column contains pathogenic variant counts.
    - Click on a "PDB" or "AlphaFold 3D" link/button in the Protein Structure column and verify it opens a valid structural viewer modal or page.

---

## Test Case 4: Guardrails & Validation (Cloud Consistency)
**Objective**: Verify that backend validation rules (Microarray + Missing Groups) correctly intercept errors and bubble them to the UI without crashing the cloud container.

**Browser Agent Instructions**:
1. Navigate back to the "Submit Run" page.
2. Submit `GSE15852` (Case: `breast tumor tissue`, Control: `normal breast tissue`).
3. **Assertions**: Assert that an Error Boundary explicitly mentioning "Microarray" or "Affymetrix" is displayed.
4. Navigate back to the "Submit Run" page.
5. Submit `GSE270454` (Case: `isolated wbc`, Control: `whole blood`).
6. **Assertions**: Assert that an Error Boundary explicitly mentioning "Could not find BOTH Case and Control samples" is displayed.

---

## Test Case 5: Cloud Storage Persistence
**Objective**: Verify that the Google Cloud Storage FUSE mount correctly saved the SQLite database and plots, allowing instant rehydration.

**Browser Agent Instructions**:
1. Navigate to the "Runs History" or "All Runs" tab on the sidebar/navbar.
2. **Assertions**:
    - Assert that `GSE270967` is listed with a "Done" status.
3. Click on the successful `GSE270967` run from the history list.
4. **Assertions**:
    - The dashboard should instantly reload all the plots, the DEG table, and the PPI network without triggering a "Running Pipeline" loading screen.

---
**End of Protocol**
