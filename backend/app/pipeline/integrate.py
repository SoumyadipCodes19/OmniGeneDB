import requests
import time

def get_uniprot_data(symbol):
    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        return None
    clean_sym = symbol.strip()
    url = f"https://rest.uniprot.org/uniprotkb/search?query=gene_exact:{clean_sym}+AND+organism_id:9606"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json()
        if not data.get("results"):
            return None
        
        best = data["results"][0]
        uniprot_id = best.get("primaryAccession")
        if not uniprot_id:
            return None
        
        function = "Function unknown"
        for comment in best.get("comments", []):
            if isinstance(comment, dict) and comment.get("commentType") == "FUNCTION":
                texts = [t.get("value") for t in comment.get("texts", []) if isinstance(t, dict) and t.get("value")]
                if texts:
                    function = texts[0]
                break
                
        domains = [f.get("description", "Unknown") for f in best.get("features", []) if isinstance(f, dict) and f.get("type") == "Domain"]
        return {
            "id": uniprot_id, 
            "function": function, 
            "domains": list(set(domains)),
            "source_url": f"https://www.uniprot.org/uniprotkb/{uniprot_id}/entry"
        }
    except Exception:
        return None

# Global KEGG Pathway Cache to prevent hammering the API and fix the /list/ bug
KEGG_PATHWAY_MAP = None

def _get_kegg_pathway_map():
    global KEGG_PATHWAY_MAP
    if KEGG_PATHWAY_MAP is None:
        try:
            res = requests.get("http://rest.kegg.jp/list/pathway/hsa", timeout=10)
            KEGG_PATHWAY_MAP = {}
            for line in res.text.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        # parts[0] is 'hsa01100', map both 'hsa01100' and 'path:hsa01100'
                        pid = parts[0]
                        name = parts[1].split(' - Homo sapiens')[0]
                        KEGG_PATHWAY_MAP[pid] = name
                        KEGG_PATHWAY_MAP["path:" + pid] = name
        except Exception:
            KEGG_PATHWAY_MAP = {}
    return KEGG_PATHWAY_MAP

def get_kegg_data(uniprot_id):
    if not uniprot_id or not isinstance(uniprot_id, str) or not uniprot_id.strip():
        return {"pathways": [], "source_url": None}
    clean_id = uniprot_id.strip()
    try:
        url_conv = f"http://rest.kegg.jp/conv/genes/uniprot:{clean_id}"
        res = requests.get(url_conv, timeout=10)
        if res.status_code != 200 or not res.text.strip():
            return {"pathways": [], "source_url": None}
            
        lines = res.text.strip().split('\n')
        if not lines or '\t' not in lines[0]:
            return {"pathways": [], "source_url": None}
        kegg_id = lines[0].split('\t')[1]
        
        res_link = requests.get(f"http://rest.kegg.jp/link/pathway/{kegg_id}", timeout=10)
        if res_link.status_code != 200 or not res_link.text.strip():
            return {"pathways": [], "source_url": f"https://www.kegg.jp/entry/{kegg_id}"}
        
        pathways = [line.split('\t')[1] for line in res_link.text.strip().split('\n') if line and '\t' in line]
        
        pathway_map = _get_kegg_pathway_map()
        names = []
        for pid in pathways[:3]:
            if pid in pathway_map:
                names.append(pathway_map[pid])
                
        return {
            "pathways": names,
            "source_url": f"https://www.kegg.jp/entry/{kegg_id}"
        }
    except Exception as e:
        print(f"KEGG error: {e}")
        return {"pathways": [], "source_url": None}

def get_string_data(symbol):
    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        return {"partners": [], "network_image_url": None, "source_url": None}
    clean_sym = symbol.strip()
    try:
        url = f"https://string-db.org/api/json/network?identifiers={clean_sym}&species=9606"
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return {"partners": [], "network_image_url": None, "source_url": None}
        data = res.json()
        if not isinstance(data, list):
            return {"partners": [], "network_image_url": None, "source_url": None}
        partners = []
        for edge in data:
            if isinstance(edge, dict):
                if edge.get("preferredName_A") == clean_sym and edge.get("preferredName_B"):
                    partners.append(edge["preferredName_B"])
                elif edge.get("preferredName_B") == clean_sym and edge.get("preferredName_A"):
                    partners.append(edge["preferredName_A"])
        return {
            "partners": list(set(partners))[:5],
            "network_image_url": f"https://string-db.org/api/image/network?identifiers={clean_sym}&species=9606",
            "source_url": f"https://string-db.org/network/9606.{clean_sym}"
        }
    except Exception:
        return {"partners": [], "network_image_url": None, "source_url": None}

def get_pdb_data(uniprot_id):
    if not uniprot_id or not isinstance(uniprot_id, str) or not uniprot_id.strip():
        return None
    clean_id = uniprot_id.strip()
    query = {
      "query": { "type": "terminal", "service": "text", "parameters": { "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession", "operator": "exact_match", "value": clean_id } },
      "return_type": "entry", "request_options": { "paginate": { "start": 0, "rows": 1 } }
    }
    try:
        res = requests.post("https://search.rcsb.org/rcsbsearch/v2/query", json=query, timeout=10)
        if res.status_code != 200 or not res.json().get("result_set"):
            return None
        pdb_id = res.json()["result_set"][0]["identifier"]
        return {
            "id": pdb_id, 
            "scop": "Available via structure", 
            "cath": "Available via structure",
            "source_url": f"https://www.rcsb.org/structure/{pdb_id}"
        }
    except Exception:
        return None

def get_ensembl_data(symbol):
    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        return {"location": "N/A", "source_url": None}
    clean_sym = symbol.strip()
    try:
        res = requests.get(f"https://rest.ensembl.org/lookup/symbol/homo_sapiens/{clean_sym}?content-type=application/json", timeout=10)
        if res.status_code == 200:
            d = res.json()
            ensembl_id = d.get('id')
            return {
                "location": f"chr{d.get('seq_region_name')}:{d.get('start')}-{d.get('end')}",
                "source_url": f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={ensembl_id}"
            }
        return {"location": "N/A", "source_url": None}
    except Exception:
        return {"location": "N/A", "source_url": None}

def get_clinvar_data(symbol):
    if not symbol or not isinstance(symbol, str) or not symbol.strip():
        return {"status": "N/A", "source_url": None}
    clean_sym = symbol.strip()
    try:
        url = f"https://www.ncbi.nlm.nih.gov/clinvar/?term={clean_sym}[gene]"
        res = requests.get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term={clean_sym}[gene]+AND+pathogenic[clnsig]&retmode=json", timeout=10)
        if res.status_code == 200:
            data = res.json()
            count = int(data.get("esearchresult", {}).get("count", 0))
            if count > 0:
                return {"status": f"Pathogenic variants reported ({count})", "source_url": url}
        res2 = requests.get(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=clinvar&term={clean_sym}[gene]&retmode=json", timeout=10)
        if res2.status_code == 200:
            data2 = res2.json()
            count2 = int(data2.get("esearchresult", {}).get("count", 0))
            if count2 > 0:
                return {"status": f"Variants reported ({count2})", "source_url": url}
        return {"status": "No variants reported", "source_url": url}
    except Exception:
        return {"status": "N/A", "source_url": None}

def check_consistency(uniprot, kegg):
    if not uniprot or not kegg or not isinstance(uniprot, dict) or not isinstance(kegg, dict):
        return True, ""
    func = uniprot.get("function", "").lower()
    pathways = " ".join(kegg.get("pathways", [])).lower()
    import re
    words_p = set(re.findall(r'\b\w{4,}\b', pathways))
    words_f = set(re.findall(r'\b\w{4,}\b', func))
    if len(words_p.intersection(words_f)) == 0 and len(words_p) > 0:
        return False, "No overlapping keywords between UniProt function and KEGG pathways."
    return True, "Consistent keywords found."

def get_alphafold_data(uniprot_id):
    if not uniprot_id or not isinstance(uniprot_id, str) or not uniprot_id.strip():
        return None
    clean_id = uniprot_id.strip()
    try:
        res = requests.get(f"https://alphafold.ebi.ac.uk/api/prediction/{clean_id}", timeout=10)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "pdbUrl" in data[0]:
                return data[0]["pdbUrl"]
    except Exception:
        pass
    return None

def get_opentargets_data(ensembl_id):
    if not ensembl_id or not isinstance(ensembl_id, str) or not ensembl_id.strip():
        return [], False
    query = """
    query {
      target(ensemblId: "%s") {
        drugAndClinicalCandidates {
          rows {
            drug { name }
          }
        }
        depMapEssentiality {
          screens { diseaseFromSource }
        }
      }
    }
    """ % ensembl_id
    try:
        url = 'https://api.platform.opentargets.org/api/v4/graphql'
        r = requests.post(url, json={"query": query}, timeout=10)
        data = r.json()
        target = data.get("data", {}).get("target")
        if not target: return [], False
        
        # Parse Drugs
        drugs_list = []
        if target.get("drugAndClinicalCandidates"):
            drugs = target.get("drugAndClinicalCandidates", {}).get("rows", [])
            drugs_list = list(set([d["drug"]["name"] for d in drugs]))[:5]
            
        # Parse DepMap
        is_essential = False
        depmap = target.get("depMapEssentiality")
        if depmap and len(depmap) > 0:
            screens = depmap[0].get("screens", [])
            if len(screens) > 0:
                is_essential = True
                
        return drugs_list, is_essential
    except:
        return [], False

def get_enrichr_tfs(symbols):
    if not symbols or not isinstance(symbols, (list, tuple, set)):
        return []
    try:
        clean_symbols = [
            str(s).strip() for s in symbols 
            if s is not None and str(s).strip() and str(s).strip() != "None" and str(s).strip() != "nan"
        ]
        clean_symbols = list(dict.fromkeys(clean_symbols))
        if not clean_symbols:
            return []

        res = requests.post(
            "https://maayanlab.cloud/Enrichr/addList",
            files={
                "list": (None, "\n".join(clean_symbols)),
                "description": (None, "OmniGeneDB")
            },
            timeout=10
        )
        if res.status_code != 200:
            return []
        user_list_id = res.json().get("userListId")
        if not user_list_id:
            return []

        res_enrich = requests.get(
            f"https://maayanlab.cloud/Enrichr/enrich?userListId={user_list_id}&backgroundType=ChEA_2022",
            timeout=10
        )
        if res_enrich.status_code != 200:
            return []
        tfs = res_enrich.json().get("ChEA_2022", [])
        # tfs format: [Rank, Term name, P-value, Z-score, Combined score, Overlapping genes, Adjusted p-value, Old p-value, Old adjusted p-value]
        top_tfs = []
        for x in tfs:
            if len(x) > 1 and x[1]:
                tf_name = str(x[1]).split()[0]
                if tf_name and tf_name not in top_tfs:
                    top_tfs.append(tf_name)
                if len(top_tfs) >= 5:
                    break
        if not top_tfs and tfs:
            top_tfs = [x[1] for x in tfs[:5] if len(x) > 1 and x[1]]
        return top_tfs
    except Exception as e:
        print(f"Enrichr error: {e}")
        return []

def get_string_ppi(deg_list):
    if not deg_list or not isinstance(deg_list, list):
        return []
    clean_symbols = [
        str(deg.get("symbol", "")).strip()
        for deg in deg_list
        if deg and deg.get("symbol") is not None and str(deg.get("symbol")).strip() and str(deg.get("symbol")).strip() != "None" and str(deg.get("symbol")).strip() != "nan"
    ]
    clean_symbols = list(dict.fromkeys(clean_symbols))
    if not clean_symbols:
        return []
    symbols = "%0d".join(clean_symbols)
    try:
        url = f"https://string-db.org/api/json/network?identifiers={symbols}&species=9606"
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return []
        data = res.json()
        if not isinstance(data, list):
            return []
        edges = []
        for edge in data:
            if isinstance(edge, dict):
                edges.append({
                    "source": edge.get("preferredName_A"),
                    "target": edge.get("preferredName_B"),
                    "score": edge.get("score")
                })
        return edges
    except Exception:
        return []

def get_gtex_eqtls(gene_symbol):
    if not gene_symbol or not isinstance(gene_symbol, str):
        return []
    clean_sym = gene_symbol.strip()
    if not clean_sym:
        return []
    try:
        # Step 1: Query GTEx API v2 reference endpoint to obtain gencodeId
        ref_url = f"https://gtexportal.org/api/v2/reference/gene?geneId={clean_sym}"
        res = requests.get(ref_url, timeout=10)
        if res.status_code != 200:
            return []
        ref_data = res.json()
        genes = ref_data.get("data", [])
        if not genes or not isinstance(genes, list):
            return []
        gencode_id = genes[0].get("gencodeId")
        if not gencode_id:
            return []
            
        # Step 2: Query singleTissueEqtl association endpoint
        eqtl_url = f"https://gtexportal.org/api/v2/association/singleTissueEqtl?gencodeId={gencode_id}&datasetId=gtex_v8&itemsPerPage=5"
        res_eqtl = requests.get(eqtl_url, timeout=10)
        if res_eqtl.status_code != 200:
            return []
        eqtl_data = res_eqtl.json()
        eqtls = []
        for eqtl in eqtl_data.get("data", [])[:5]:
            eqtls.append({
                "tissueSiteDetailId": eqtl.get("tissueSiteDetailId"),
                "variantId": eqtl.get("variantId") or eqtl.get("snpId"),
                "snpId": eqtl.get("snpId"),
                "nes": eqtl.get("nes"),
                "pValue": eqtl.get("pValue")
            })
        return eqtls
    except Exception:
        return []

def get_tcga_survival(ensembl_id):
    if not ensembl_id or not isinstance(ensembl_id, str) or not ensembl_id.strip():
        return False
    clean_id = ensembl_id.strip()
    query = """
    query {
      target(ensemblId: "%s") {
        hallmarks {
          cancerHallmarks { label }
        }
      }
    }
    """ % clean_id
    try:
        url = 'https://api.platform.opentargets.org/api/v4/graphql'
        r = requests.post(url, json={"query": query}, timeout=10)
        if r.status_code != 200:
            return False
        data = r.json()
        target = data.get("data", {}).get("target")
        if not target:
            return False
        
        hallmarks = target.get("hallmarks")
        if hallmarks and hallmarks.get("cancerHallmarks"):
            return True
        return False
    except Exception:
        return False

def run_integration(deg_list, is_cancer=False):
    """
    Takes a list of dictionaries [{'symbol': '...', 'log2fc': ..., 'padj': ..., 'baseMean': ...}]
    and returns fully integrated records, plus global TF data and ppi_network.
    """
    integrated = []
    
    symbols = [
        str(deg.get("symbol", "")).strip() 
        for deg in deg_list 
        if deg and deg.get("symbol") is not None and str(deg.get("symbol")).strip()
    ]
    global_tfs = get_enrichr_tfs(symbols)
    ppi_network = get_string_ppi(deg_list)
    
    for deg in deg_list:
        symbol = str(deg.get("symbol", "")).strip()
        record = {
            "symbol": symbol,
            "log2fc": deg.get("log2fc"),
            "padj": deg.get("padj"),
            "baseMean": deg.get("baseMean")
        }
        
        uniprot = get_uniprot_data(symbol)
        record["uniprot"] = uniprot
        
        kegg = {"pathways": []}
        pdb = None
        alphafold_url = None
        if uniprot and uniprot.get("id"):
            kegg = get_kegg_data(uniprot["id"])
            pdb = get_pdb_data(uniprot["id"])
            if not pdb:
                alphafold_url = get_alphafold_data(uniprot["id"])
            
        record["kegg"] = kegg
        record["pdb"] = pdb
        record["alphafold_url"] = alphafold_url
        record["string"] = get_string_data(symbol)
        
        record["clinvar"] = get_clinvar_data(symbol)
        record["genomic"] = get_ensembl_data(symbol)
        
        ensembl_id = None
        if record["genomic"].get("source_url") and "g=" in record["genomic"]["source_url"]:
            ensembl_id = record["genomic"]["source_url"].split("g=")[-1]
        
        drugs, is_essential = get_opentargets_data(ensembl_id)
        record["drugs"] = drugs
        record["depmap_essential"] = is_essential
        
        record["eqtl"] = get_gtex_eqtls(symbol)
        record["tcga_survival"] = get_tcga_survival(ensembl_id) if is_cancer else False
        
        is_consistent, note = check_consistency(uniprot, kegg)
        record["consistency_flag"] = is_consistent
        record["consistency_note"] = note
        
        missing = []
        if not uniprot: missing.append("UniProt Function")
        if not kegg.get("pathways"): missing.append("KEGG Pathways")
        if not pdb and not alphafold_url: missing.append("3D Structure (PDB/AlphaFold)")
        if not record["string"].get("network_image_url"): missing.append("STRING Interactions")
        if record["clinvar"].get("status") in ("No variants reported", "N/A"): missing.append("ClinVar Variants")
        if not record["drugs"]: missing.append("OpenTargets Drugs")
        
        record["coverage_gaps"] = missing
        integrated.append(record)
        time.sleep(0.5) # Rate limit protection
        
    return {
        "results": integrated,
        "master_tfs": global_tfs,
        "ppi_network": ppi_network
    }

# Function aliases for external consumers / tests
get_uniprot_info = get_uniprot_data
get_opentargets_drugs = get_opentargets_data
get_kegg_pathways = get_kegg_data
