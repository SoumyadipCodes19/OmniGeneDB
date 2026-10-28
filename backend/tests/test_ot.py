import requests

query = """
query {
  search(queryString: "TP53", entityNames: ["target"]) {
    hits { id }
  }
}
"""
url = 'https://api.platform.opentargets.org/api/v4/graphql'
r = requests.post(url, json={"query": query})
print(r.json())
