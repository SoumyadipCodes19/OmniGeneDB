import requests
query = """query { target(ensemblId: "ENSG00000012048") { hallmarks { cancerHallmarks { label } } } }"""
r = requests.post("https://api.platform.opentargets.org/api/v4/graphql", json={"query": query})
print(r.json())
