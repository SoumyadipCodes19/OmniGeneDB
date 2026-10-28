import urllib.request

gses = [190364, 137094, 219504, 169002, 194458, 203870, 204902, 153310, 199047, 136666, 171630, 139158, 142171]

for g in gses:
    url = f'https://www.ncbi.nlm.nih.gov/geo/download/?format=file&type=rnaseq_counts&acc=GSE{g}&file=GSE{g}_raw_counts_GRCh38.p13_NCBI.tsv.gz'
    try:
        req = urllib.request.Request(url, method='HEAD')
        resp = urllib.request.urlopen(req)
        print(f"GSE{g}: {resp.getcode()}")
    except Exception as e:
        print(f"GSE{g}: {e}")
