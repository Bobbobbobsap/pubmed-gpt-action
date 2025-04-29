import requests
from fastapi import FastAPI, Query
from xml.etree import ElementTree as ET

app = FastAPI()

# -------- PubMed検索 --------
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
            try:
                root = ET.fromstring(fetch_response.text)
                title = root.findtext(".//ArticleTitle") or "タイトル取得失敗"
            except Exception:
                title = "タイトル取得失敗"
        else:
            title = "タイトル取得失敗"

        results.append({
            "pmid": pmid,
            "title": title,
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        })

    return {"papers": results}

# -------- Crossref検索 --------
def get_crossref_metadata(doi):
    url = f"https://api.crossref.org/works/{doi}"
    response = requests.get(url)
    if response.status_code != 200:
        return {"error": f"DOI {doi} not found"}

    data = response.json()["message"]
    return {
        "title": data.get("title", [""])[0],
        "authors": [f"{a.get('given', '')} {a.get('family', '')}" for a in data.get("author", [])],
        "journal": data.get("container-title", [""])[0],
        "published": data.get("issued", {}).get("date-parts", [[""]])[0],
        "abstract": data.get("abstract", "（抄録はありません）")
    }

@app.get("/get_metadata")
def get_metadata(doi: str = Query(..., description="DOI (Digital Object Identifier)")):
    return get_crossref_metadata(doi)