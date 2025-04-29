import requests
from fastapi import FastAPI, Query

app = FastAPI()

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