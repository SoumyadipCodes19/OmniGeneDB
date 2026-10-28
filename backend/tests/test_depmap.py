import requests

query = """
query {
  target(ensemblId: "ENSG00000141510") {
    depMapEssentiality {
      screens { diseaseFromSource }
    }
  }
}
"""
url = 'https://api.platform.opentargets.org/api/v4/graphql'
r = requests.post(url, json={"query": query})
data = r.json()
deps = data.get("data",{}).get("target",{}).get("depMapEssentiality",[])
if deps:
    print(deps[0])
