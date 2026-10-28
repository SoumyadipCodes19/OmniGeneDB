#!/usr/bin/env Rscript
args = commandArgs(trailingOnly=TRUE)

if (length(args) < 3) {
  stop("Usage: run_deseq2.R <counts_csv> <coldata_csv> <output_csv>")
}

counts_file <- args[1]
coldata_file <- args[2]
output_file <- args[3]

suppressMessages(library(DESeq2))

# Load data
counts_data <- read.csv(counts_file, row.names=1)
coldata <- read.csv(coldata_file, row.names=1)

# Ensure sample names match
common_samples <- intersect(colnames(counts_data), rownames(coldata))
counts_data <- counts_data[, common_samples]
coldata <- coldata[common_samples, , drop=FALSE]

# Ensure grouping factor is set with Control as the baseline reference level
if ("Control" %in% coldata$Group) {
  coldata$Group <- relevel(factor(coldata$Group), ref="Control")
} else {
  coldata$Group <- as.factor(coldata$Group)
}

# Pre-filter
keep <- rowSums(counts_data >= 10) >= min(table(coldata$Group))
counts_data <- counts_data[keep, ]

# Run DESeq2
# Using sfType="poscount" is safer for varying GEO datasets (e.g., handles zeros better in some datasets)
dds <- DESeqDataSetFromMatrix(countData=counts_data, colData=coldata, design=~Group)
dds <- DESeq(dds, test="Wald", sfType="poscount")

# Get results
res <- results(dds, alpha=0.05, pAdjustMethod="fdr")
res_ordered <- res[order(res$padj), ]

# Format output
out_df <- as.data.frame(res_ordered)
out_df$GeneID <- rownames(out_df)
out_df <- out_df[, c("GeneID", "baseMean", "log2FoldChange", "lfcSE", "stat", "pvalue", "padj")]
write.csv(out_df, file=output_file, row.names=FALSE)

# Generate Plots
suppressMessages(library(ggplot2))
dir_path <- dirname(output_file)

# Volcano Plot
res_plot <- as.data.frame(res)
res_plot$sig <- ifelse(!is.na(res_plot$padj) & res_plot$padj < 0.05 & abs(res_plot$log2FoldChange) > 1, "Significant", "Not Significant")
volcano <- ggplot(res_plot, aes(x=log2FoldChange, y=-log10(padj), color=sig)) + 
  geom_point(alpha=0.6, size=1.5) +
  scale_color_manual(values=c("Not Significant"="grey", "Significant"="red")) +
  theme_minimal() + 
  labs(title="Volcano Plot", x="Log2 Fold Change", y="-Log10(padj)")
ggsave(file.path(dir_path, "volcano.png"), plot=volcano, width=6, height=5, bg="white")

# PCA Plot
ntd <- normTransform(dds)
pcaData <- plotPCA(ntd, intgroup=c("Group"), returnData=TRUE)
percentVar <- round(100 * attr(pcaData, "percentVar"))
pca <- ggplot(pcaData, aes(PC1, PC2, color=Group)) +
  geom_point(size=3) +
  xlab(paste0("PC1: ", percentVar[1], "% variance")) +
  ylab(paste0("PC2: ", percentVar[2], "% variance")) + 
  theme_minimal() +
  labs(title="PCA Plot")
ggsave(file.path(dir_path, "pca.png"), plot=pca, width=6, height=5, bg="white")

# Gene ID mapping and list preparation for functional enrichment
geneList <- NULL
entrez_map <- NULL
key_type <- "SYMBOL"

tryCatch({
  suppressMessages(library(clusterProfiler))
  suppressMessages(library(org.Hs.eg.db))
  suppressMessages(library(enrichplot))
  
  res_na_rm <- res_plot[!is.na(res_plot$log2FoldChange) & !is.na(res_plot$padj), ]
  rn <- rownames(res_na_rm)
  
  if (all(grepl("^[0-9]+$", rn))) {
    key_type <- "ENTREZID"
  } else if (all(grepl("^ENSG", rn))) {
    key_type <- "ENSEMBL"
  } else {
    key_type <- "SYMBOL"
  }
  
  entrez_map <- tryCatch({
    suppressMessages(select(org.Hs.eg.db, keys=rn, columns=c("ENTREZID", "SYMBOL"), keytype=key_type))
  }, error = function(e) {
    cat("Annotation lookup warning:", e$message, "\n")
    NULL
  })
  
  if (!is.null(entrez_map) && nrow(entrez_map) > 0) {
    res_na_rm$ENTREZID <- entrez_map$ENTREZID[match(rownames(res_na_rm), entrez_map[[key_type]])]
    res_valid <- res_na_rm[!is.na(res_na_rm$ENTREZID), ]
    
    gl <- res_valid$log2FoldChange
    names(gl) <- res_valid$ENTREZID
    gl <- sort(gl, decreasing = TRUE)
    geneList <- gl[!duplicated(names(gl))]
  }
}, error = function(e) {
  cat("Error preparing gene list for enrichment:", e$message, "\n")
})

# GSEA GO Biological Processes
tryCatch({
  if (!is.null(geneList) && length(geneList) > 0) {
    gse_go <- gseGO(geneList = geneList, OrgDb = org.Hs.eg.db, keyType = "ENTREZID", ont = "BP", pvalueCutoff = 0.05, pAdjustMethod = "BH", verbose = FALSE)
    if (!is.null(gse_go) && nrow(as.data.frame(gse_go)) > 0) {
      if (requireNamespace("ggridges", quietly = TRUE)) {
        p_go <- ridgeplot(gse_go) + ggtitle("GSEA GO Biological Processes")
      } else {
        p_go <- enrichplot::dotplot(gse_go) + ggtitle("GSEA GO Biological Processes")
      }
      ggsave(file.path(dir_path, "go_enrichment.png"), plot=p_go, width=8, height=6, bg="white")
      cat("Saved go_enrichment.png successfully.\n")
    } else {
      cat("No significant GSEA GO terms found.\n")
    }
  } else {
    cat("No valid Entrez IDs for GSEA GO.\n")
  }
}, error = function(e) {
  cat("Skipping GSEA GO enrichment:", e$message, "\n")
})

# GSEA KEGG Pathways
tryCatch({
  if (!is.null(geneList) && length(geneList) > 0) {
    gse_kegg <- gseKEGG(geneList = geneList, organism = 'hsa', pvalueCutoff = 0.05, verbose = FALSE)
    if (!is.null(gse_kegg) && nrow(as.data.frame(gse_kegg)) > 0) {
      if (requireNamespace("ggridges", quietly = TRUE)) {
        p_kegg <- ridgeplot(gse_kegg) + ggtitle("GSEA KEGG Pathways")
      } else {
        p_kegg <- enrichplot::dotplot(gse_kegg) + ggtitle("GSEA KEGG Pathways")
      }
      ggsave(file.path(dir_path, "kegg_enrichment.png"), plot=p_kegg, width=8, height=6, bg="white")
      cat("Saved kegg_enrichment.png successfully.\n")
    } else {
      cat("No significant GSEA KEGG pathways found.\n")
    }
  } else {
    cat("No valid Entrez IDs for GSEA KEGG.\n")
  }
}, error = function(e) {
  cat("Skipping GSEA KEGG enrichment:", e$message, "\n")
})

# MCPcounter Immune Deconvolution
tryCatch({
  if (requireNamespace("MCPcounter", quietly = TRUE)) {
    suppressMessages(library(MCPcounter))
    expr_mat <- assay(ntd)
    
    if (!is.null(entrez_map) && key_type %in% colnames(entrez_map)) {
      symbol_map <- entrez_map$SYMBOL[match(rownames(expr_mat), entrez_map[[key_type]])]
      valid_idx <- !is.na(symbol_map)
      expr_mat <- expr_mat[valid_idx, , drop=FALSE]
      symbol_map <- symbol_map[valid_idx]
      
      if (length(symbol_map) > 0) {
        expr_mat_sym <- aggregate(expr_mat, by=list(Symbol=symbol_map), FUN=mean)
        rownames(expr_mat_sym) <- expr_mat_sym$Symbol
        expr_mat_sym$Symbol <- NULL
        
        mcp_res <- MCPcounter.estimate(as.matrix(expr_mat_sym), featuresType = "HUGO_symbols")
        
        mcp_melt <- reshape2::melt(mcp_res)
        colnames(mcp_melt) <- c("CellType", "Sample", "Score")
        mcp_melt$Group <- coldata[as.character(mcp_melt$Sample), "Group"]
        
        p_mcp <- ggplot(mcp_melt, aes(x=Sample, y=Score, fill=CellType)) +
          geom_bar(stat="identity", position="fill") +
          facet_wrap(~Group, scales="free_x") +
          theme_minimal() +
          theme(axis.text.x = element_text(angle=90, hjust=1)) +
          labs(title="Immune Deconvolution (MCPcounter)", x="Sample", y="Relative Fraction", fill="Cell Population")
        
        ggsave(file.path(dir_path, "immune_infiltration.png"), plot=p_mcp, width=10, height=6, bg="white")
        write.csv(mcp_res, file.path(dir_path, "mcp_results.csv"))
        cat("Saved immune_infiltration.png and mcp_results.csv successfully.\n")
      } else {
        cat("No valid SYMBOLs found for MCPcounter.\n")
      }
    }
  } else {
    cat("MCPcounter package is not installed; skipping immune deconvolution.\n")
  }
}, error = function(e) {
  cat("Skipping MCPcounter deconvolution:", e$message, "\n")
})

cat("DESeq2 analysis completed successfully.\n")
