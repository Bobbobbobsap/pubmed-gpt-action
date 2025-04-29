# app.py
from fastapi import FastAPI, Query
import requests

app = FastAPI()

@app.get("/search_papers")
def search_papers(keyword: str = Query(..., description="検索するキーワード")):
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": keyword,
        "retmode": "json",
        "retmax": 5
    }
    response = requests.get(url, params=params)
    data = response.json()

    pmids = data.get('esearchresult', {}).get('idlist', [])
    results = []
    for pmid in pmids:
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml"
        }
        fetch_response = requests.get(fetch_url, params=fetch_params)
        if fetch_response.status_code == 200:
            results.append({
                "pmid": pmid,
                "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            })

    return {"papers": results}
