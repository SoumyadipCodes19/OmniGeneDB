import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { transformWithOxc } from 'vite';
import { renderToStaticMarkup } from 'react-dom/server';
import React from 'react';
import { jsx as _jsx, jsxs as _jsxs } from 'react/jsx-runtime';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

async function runEdgeCaseTests() {
  console.log("======================================================================");
  console.log("CHALLENGER 2: FRONTEND RENDERING EDGE-CASE TEST SUITE");
  console.log("======================================================================");

  // ------------------------------------------------------------------
  // Test 1: ErrorBoundary Component
  // ------------------------------------------------------------------
  console.log("\n--- Test 1: ErrorBoundary Stress & Fallback Verification ---");
  const errorBoundaryPath = path.resolve(__dirname, 'src/components/ErrorBoundary.tsx');
  const ebSource = fs.readFileSync(errorBoundaryPath, 'utf-8');
  const ebTransformed = await transformWithOxc(ebSource, 'ErrorBoundary.tsx', { lang: 'tsx' });
  
  // Write to temporary module file for dynamic import
  const ebTempPath = path.resolve(__dirname, 'temp_error_boundary.mjs');
  fs.writeFileSync(ebTempPath, ebTransformed.code);

  try {
    const { ErrorBoundary } = await import('./temp_error_boundary.mjs');
    
    // 1.1 Verify clean pass-through when no error
    const normalHtml = renderToStaticMarkup(
      React.createElement(ErrorBoundary, null, 
        React.createElement('div', { id: 'child-content' }, 'All systems nominal')
      )
    );
    assert(normalHtml.includes('All systems nominal'), "ErrorBoundary failed to render children under normal operation");
    console.log("PASS: ErrorBoundary cleanly renders children when no errors occur.");

    // 1.2 Verify static getDerivedStateFromError
    const testError = new Error("Simulated fatal React rendering explosion");
    const derivedState = ErrorBoundary.getDerivedStateFromError(testError);
    assert(derivedState.hasError === true, "getDerivedStateFromError must set hasError = true");
    assert(derivedState.error === testError, "getDerivedStateFromError must store the error object");

    // 1.3 Verify rendering fallback UI when in error state
    const ebInstance = new ErrorBoundary({ children: React.createElement('div', null, 'Unreachable') });
    ebInstance.state = {
      hasError: true,
      error: testError,
      errorInfo: { componentStack: "\n    in BuggyComponent\n    in App" }
    };

    const fallbackHtml = renderToStaticMarkup(ebInstance.render());
    assert(fallbackHtml.includes("Rendering Error Encountered"), "Fallback UI missing 'Rendering Error Encountered' heading");
    assert(fallbackHtml.includes("Simulated fatal React rendering explosion"), "Fallback UI missing error message");
    assert(fallbackHtml.includes("Try Again"), "Fallback UI missing 'Try Again' reset button");
    assert(fallbackHtml.includes("Reload Page"), "Fallback UI missing 'Reload Page' button");
    assert(fallbackHtml.includes("BuggyComponent"), "Fallback UI missing component stack trace");
    console.log("PASS: ErrorBoundary renders complete recovery UI with stack trace upon error state.");

    // 1.4 Verify custom fallback support
    const customEb = new ErrorBoundary({
      children: React.createElement('div', null, 'Unreachable'),
      fallback: React.createElement('div', { className: 'custom-fallback' }, 'Custom safe placeholder')
    });
    customEb.state = { hasError: true, error: testError, errorInfo: null };
    const customHtml = renderToStaticMarkup(customEb.render());
    assert(customHtml.includes('Custom safe placeholder'), "ErrorBoundary did not render custom fallback");
    console.log("PASS: ErrorBoundary supports custom fallback rendering.");

  } finally {
    if (fs.existsSync(ebTempPath)) fs.unlinkSync(ebTempPath);
  }

  // ------------------------------------------------------------------
  // Test 2: PlotCard Fallback Rendering
  // ------------------------------------------------------------------
  console.log("\n--- Test 2: PlotCard Missing Plot Fallbacks ---");
  const appPath = path.resolve(__dirname, 'src/App.tsx');
  const appSource = fs.readFileSync(appPath, 'utf-8');

  // Extract PlotCard definition and dependencies
  const plotCardMatch = appSource.match(/interface PlotCardProps[\s\S]*?function PlotCard[\s\S]*?\n\}/);
  assert(plotCardMatch, "Could not locate PlotCard component in App.tsx");

  const plotCardCode = `
import React, { useState, useEffect } from 'react';
import { BarChart3, RotateCw } from 'lucide-react';
${plotCardMatch[0]}
export { PlotCard };
`;

  const pcTransformed = await transformWithOxc(plotCardCode, 'PlotCard.tsx', { lang: 'tsx' });
  const pcTempPath = path.resolve(__dirname, 'temp_plot_card.mjs');
  fs.writeFileSync(pcTempPath, pcTransformed.code);

  try {
    const { PlotCard } = await import('./temp_plot_card.mjs');

    // 2.1 Normal initial render
    const normalPlotHtml = renderToStaticMarkup(
      React.createElement(PlotCard, {
        title: "Volcano Plot",
        subtitle: "Differential expression overview",
        src: "/plots/GSE270967/volcano.png",
        alt: "Volcano plot"
      })
    );
    assert(normalPlotHtml.includes("Volcano Plot"), "PlotCard missing title");
    assert(normalPlotHtml.includes("volcano.png"), "PlotCard missing img element");

    // 2.2 Error / Missing fallback state
    // Simulate PlotCard internal rendering when hasError = true
    // We inspect the fallback branch in PlotCard:
    // When hasError = true: renders BarChart3, emptyMessage, and 'No visualization generated'
    assert(appSource.includes("emptyMessage = 'Plot not available'"), "PlotCard missing default emptyMessage parameter");
    assert(appSource.includes("No visualization generated for this dataset or image is unavailable"), "PlotCard missing fallback description");
    assert(appSource.includes("onError={() => {"), "PlotCard missing onError handler");
    assert(appSource.includes("setHasError(true)"), "PlotCard missing setHasError(true) call");

    console.log("PASS: PlotCard handles missing plots with dedicated placeholder and avoids empty broken boxes.");

  } finally {
    if (fs.existsSync(pcTempPath)) fs.unlinkSync(pcTempPath);
  }

  // ------------------------------------------------------------------
  // Test 3: ResultsTable Edge Cases (null padj, null baseMean, null log2fc, unannotated)
  // ------------------------------------------------------------------
  console.log("\n--- Test 3: ResultsTable Edge-Case Data Rendering ---");

  // Extract getGeneBiotype and ResultsTable from App.tsx
  const biotypeMatch = appSource.match(/function getGeneBiotype[\s\S]*?\n\}/);
  const resultsTableMatch = appSource.match(/function ResultsTable[\s\S]*?\n\}/);
  assert(biotypeMatch, "Could not locate getGeneBiotype in App.tsx");
  assert(resultsTableMatch, "Could not locate ResultsTable in App.tsx");

  const resultsTableModuleCode = `
import React, { useState } from 'react';
import { Activity } from 'lucide-react';
${biotypeMatch[0]}
${resultsTableMatch[0]}
export { getGeneBiotype, ResultsTable };
`;

  const rtTransformed = await transformWithOxc(resultsTableModuleCode, 'ResultsTable.tsx', { lang: 'tsx' });
  const rtTempPath = path.resolve(__dirname, 'temp_results_table.mjs');
  fs.writeFileSync(rtTempPath, rtTransformed.code);

  try {
    const { getGeneBiotype, ResultsTable } = await import('./temp_results_table.mjs');

    // 3.1 Test getGeneBiotype across edge case symbols
    const locBio = getGeneBiotype("LOC102723847", {});
    assert(locBio.label === "Unannotated Locus" && locBio.isUnannotated === true, "LOC biotype mismatch");

    const numBio = getGeneBiotype("105378790", {});
    assert(numBio.label === "Unannotated Locus" && numBio.isUnannotated === true, "Numeric ID biotype mismatch");

    const lincBio = getGeneBiotype("LINC01914", {});
    assert(lincBio.label === "lncRNA" && lincBio.isUnannotated === false, "LINC biotype mismatch");

    const emptyBio = getGeneBiotype("", {});
    assert(emptyBio.label === "Unknown Locus" && emptyBio.isUnannotated === true, "Empty symbol biotype mismatch");

    const codingBio = getGeneBiotype("TP53", { uniprot: { function: "Tumor suppressor" } });
    assert(codingBio.label === "Protein Coding" && codingBio.isUnannotated === false, "TP53 biotype mismatch");
    console.log("PASS: getGeneBiotype accurately classifies unannotated loci, lncRNAs, and coding genes.");

    // 3.2 Test ResultsTable with an array of adversarial edge-case rows
    const adversarialRows = [
      // Case 1: Unannotated LOC with null metrics
      {
        symbol: "LOC102723847",
        log2fc: null,
        padj: null,
        baseMean: null,
        uniprot: null,
        kegg: { pathways: [] },
        drugs: [],
        eqtl: [],
        clinvar: { status: "N/A" },
        pdb: null,
        alphafold_url: null,
      },
      // Case 2: Numeric Entrez ID with undefined metrics
      {
        symbol: "105378790",
        log2fc: undefined,
        padj: undefined,
        baseMean: undefined,
        uniprot: undefined,
        kegg: undefined,
        drugs: undefined,
        eqtl: undefined,
        clinvar: undefined,
      },
      // Case 3: lncRNA with NaN string metrics
      {
        symbol: "LINC01914",
        log2fc: "NaN",
        padj: "NaN",
        baseMean: "NaN",
        depmap_essential: true,
        tcga_survival: true,
      },
      // Case 4: Nonexistent / completely empty row
      {},
      // Case 5: Empty string symbol
      {
        symbol: "",
        log2fc: 0.0,
        padj: 0.04,
        baseMean: 100.0,
      },
      // Case 6: Fully populated annotated control gene
      {
        symbol: "TP53",
        log2fc: 3.42,
        padj: 0.000012,
        baseMean: 2450.8,
        uniprot: { function: "Acts as a tumor suppressor in many tumor types", source_url: "https://uniprot.org/P04637" },
        kegg: { pathways: ["p53 signaling pathway", "Apoptosis"], source_url: "https://kegg.jp" },
        drugs: ["Nutlin-3", "Idasanutlin"],
        eqtl: [{ tissueSiteDetailId: "Skin", variantId: "rs143094271" }],
        clinvar: { status: "Pathogenic variants reported (120)", source_url: "https://clinvar.gov" },
        pdb: { id: "1TUP" },
        alphafold_url: "https://alphafold.ebi.ac.uk",
      }
    ];

    console.log(`Rendering ResultsTable with ${adversarialRows.length} edge-case rows...`);
    const tableHtml = renderToStaticMarkup(
      React.createElement(ResultsTable, { data: adversarialRows })
    );

    // Verify critical elements are present and didn't crash
    assert(tableHtml.includes("LOC102723847"), "LOC102723847 not rendered in table");
    assert(tableHtml.includes("105378790"), "105378790 not rendered in table");
    assert(tableHtml.includes("LINC01914"), "LINC01914 not rendered in table");
    assert(tableHtml.includes("TP53"), "TP53 not rendered in table");

    // Verify fallback badges and text
    assert(tableHtml.includes("Unannotated Locus"), "Missing 'Unannotated Locus' badge");
    assert(tableHtml.includes("Unannotated / non-protein locus"), "Missing unannotated function fallback");
    assert(tableHtml.includes("No KEGG annotation"), "Missing unannotated KEGG fallback");
    assert(tableHtml.includes("Non-coding / No Structure"), "Missing unannotated structure fallback");

    // Verify N/A rendered for null statistics
    assert(tableHtml.includes("N/A"), "Missing 'N/A' fallback for null statistical fields");

    // Verify Base Mean and Adj. P-Value headers exist
    assert(tableHtml.includes("Base Mean"), "Missing 'Base Mean' table header");
    assert(tableHtml.includes("Adj. P-Value (padj)"), "Missing 'Adj. P-Value (padj)' table header");

    // Verify scientific notation formatting for small padj (TP53: 1.200e-5)
    assert(tableHtml.includes("1.200e-5"), "padj < 0.001 was not formatted in scientific notation");

    // 3.3 Test empty data array
    const emptyTableHtml = renderToStaticMarkup(
      React.createElement(ResultsTable, { data: [] })
    );
    assert(emptyTableHtml.includes("No differential expression records found"), "Empty table fallback text missing");
    console.log("PASS: ResultsTable safely renders all null/missing fields, unannotated loci, and empty tables.");

  } finally {
    if (fs.existsSync(rtTempPath)) fs.unlinkSync(rtTempPath);
  }

  console.log("\n======================================================================");
  console.log("ALL FRONTEND RENDERING EDGE-CASE TESTS PASSED SUCCESSFULLY!");
  console.log("======================================================================");
}

function assert(condition, message) {
  if (!condition) {
    throw new Error("Assertion failed: " + message);
  }
}

runEdgeCaseTests().catch((err) => {
  console.error("Test failed with error:", err);
  process.exit(1);
});
