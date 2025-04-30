import requests
from fastapi import FastAPI, Query
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET

app = FastAPI()
# --------- ウォームアップ用エンドポイント ---------

@app.get("/ping")
def ping():
    return {"status": "ok"}

# -------- PubMed検索 --------
@app.get("/search_papers")
def search_papers(keyword: str = Query(..., description="検索するキーワード")):
    # PubMed検索
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": keyword,
        "retmode": "json",
        "retmax": 10
    }
    response = requests.get(url, params=params)
    data = response.json()

    pmids = data.get('esearchresult', {}).get('idlist', [])
    results = []

    # PubMedから詳細情報取得
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
                doi = root.findtext(".//ArticleId[@IdType='doi']")
            except Exception:
                title = "タイトル取得失敗"
                doi = "DOI not found"
        else:
            title = "タイトル取得失敗"
            doi = "DOI not found"

        # Crossrefからメタデータを取得するためにDOIを渡す
        metadata = get_crossref_metadata(doi) if doi != "DOI not found" else {}

        results.append({
            "pmid": pmid,
            "title": title,
            "doi": doi,
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "crossref_metadata": metadata
        })

    # Google Scholar から検索結果を取得
    # google_scholar_papers = get_google_scholar_papers(keyword)

    # bioRxiv から検索結果を取得
    biorxiv_papers = get_biorxiv_papers(keyword)

    # 結果を統合
    all_papers = results + biorxiv_papers

    return {"papers": all_papers}




# -------- bioRxiv検索 --------
def get_biorxiv_papers(keyword):
    url = f"https://api.biorxiv.org/details/2022/03/01/{keyword}/json"
    response = requests.get(url)

    try:
        data = response.json()
    except Exception:
        return [{"title": "bioRxivデータ取得失敗", "link": "", "source": "bioRxiv"}]

    results = []
    for item in data.get('collection', []):
        results.append({
            "title": item.get('title', 'No title'),
            "link": item.get('link', 'No link'),
            "source": "bioRxiv"
        })
    return results


# -------- Crossref検索 --------
def get_crossref_metadata(doi):
    if doi == "DOI not found":
        return {
            "title": "",
            "authors": [],
            "journal": "",
            "published": [],
            "abstract": "（DOIが見つかりませんでした）"
        }

    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.get(url)
        if response.status_code != 200:
            raise ValueError(f"DOI {doi} not found")
        data = response.json().get("message", {})

        # 抄録のHTMLタグを除去
        raw_abstract = data.get("abstract", "（抄録はありません）")
        soup = BeautifulSoup(raw_abstract, "html.parser")
        abstract = soup.get_text()

        return {
            "title": data.get("title", [""])[0],
            "authors": [f"{a.get('given', '')} {a.get('family', '')}" for a in data.get("author", [])],
            "journal": data.get("container-title", [""])[0],
            "published": data.get("issued", {}).get("date-parts", [[""]])[0],
            "abstract": abstract
        }

    except Exception:
        return {
            "title": "",
            "authors": [],
            "journal": "",
            "published": [],
            "abstract": "（Crossrefメタデータ取得失敗）"
        }


@app.get("/get_metadata")
def get_metadata(doi: str = Query(..., description="DOI (Digital Object Identifier)")):
    return get_crossref_metadata(doi)
