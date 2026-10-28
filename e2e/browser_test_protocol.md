# OmniGeneDB Browser Agent E2E Testing Protocol

This document contains standard operating procedures (SOPs) and prompts for the Antigravity Browser Agent. 
To run these tests, open the chat and type:
`/browser execute all test cases in e2e/browser_test_protocol.md on http://localhost:3001`

---

## Prerequisites
Before starting, ensure that:
1. The backend FastAPI server is running on `http://localhost:8002`.
2. The frontend Vite server is running on `http://localhost:3001`.
3. The database is initialized and clear of corrupt runs.

---

## Test Case 1: The Happy Path (RNA-Seq Differential Expression)
**Objective**: Verify that a valid RNA-seq dataset successfully completes the entire pipeline and renders all biological cards.

**Browser Agent Instructions**:
1. Navigate to `http://localhost:3001`.
2. Locate the "Submit Run" or "New Analysis" form.
3. In the "GEO Accession" input field, type `GSE270967`.
4. Click outside the input box or wait a moment to trigger the automatic metadata scanner.
5. Assert that a "Suggested Groups" or metadata badge appears on the screen, showing strings like `non-responder (rd)` and `responder (pcr)`.
6. Enter `non-responder (rd)` into the **Case Group** input.
7. Enter `responder (pcr)` into the **Control Group** input.
8. Ensure the "Is this a Cancer/Oncology dataset?" checkbox is checked (since this is breast cancer).
9. Click the primary "Submit" or "Run Pipeline" button.
10. **Wait** for the pipeline to finish (this may take 1-3 minutes). Monitor the loading state.
11. **Assertions**: Once the results page loads, verify the following elements exist on the screen:
    - A "Master Transcription Factors" card containing text.
    - A "Volcano (Significance)" plot canvas/image.
    - A "PCA (Variance)" plot canvas/image.
    - The "Top Differentially Expressed Genes" data table.
    - Inside the table, verify that there are columns for "Known Drugs (OpenTargets)", "eQTLs", and "ClinVar".

---

## Test Case 2: Multi-Omics Guardrail (Microarray Rejection)
**Objective**: Verify that the system intercepts Microarray datasets before crashing the R engine, and displays a user-friendly error.

**Browser Agent Instructions**:
1. Navigate back to the "Submit Run" page on `http://localhost:3001`.
2. In the "GEO Accession" input field, type `GSE15852`.
3. Enter `breast tumor tissue` into the **Case Group**.
4. Enter `normal breast tissue` into the **Control Group**.
5. Click "Submit".
6. **Assertions**: 
    - The pipeline should fail relatively quickly (under 30 seconds).
    - Assert that a red Error Boundary or Error Card is displayed on the screen.
    - Assert that the error text explicitly mentions "Microarray", "Affymetrix", or "RNA-Seq". 
    - Assert that the application did NOT white-screen or crash entirely (you should still see the navigation bar).

---

## Test Case 3: Validation Logic (Missing Case/Control Group)
**Objective**: Verify that the system correctly rejects submissions where the requested Case/Control groups do not exist in the dataset.

**Browser Agent Instructions**:
1. Navigate to the "Submit Run" page.
2. In the "GEO Accession" input field, type `GSE270454`.
3. Enter `isolated wbc` into the **Case Group**.
4. Enter `whole blood` into the **Control Group**.
5. Click "Submit".
6. **Assertions**:
    - The pipeline should fail.
    - Assert that the error message explicitly states something like "Could not find BOTH Case and Control samples".
    - The raw DESeq2 stack trace (e.g., `design has a single variable`) should NOT be the primary error message shown to the user.

---

## Test Case 4: History and Persistence
**Objective**: Verify that successful and failed runs are saved to the SQLite database and can be reloaded instantly.

**Browser Agent Instructions**:
1. Navigate to the "Runs History" or "All Runs" tab on the sidebar/navbar.
2. **Assertions**:
    - You should see a list of past runs.
    - Assert that `GSE270967` is listed with a "Done" or "Success" status.
    - Assert that `GSE15852` and `GSE270454` are listed with a "Failed" status.
3. Click on the successful `GSE270967` run from the history list.
4. **Assertions**:
    - The dashboard should instantly reload all the plots, the DEG table, and the PPI network without re-running the DESeq2 pipeline.
    - Verify the "Top Differentially Expressed Genes" table is visible again.

---
**End of Protocol**
