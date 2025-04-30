import requests
from fastapi import FastAPI, Query
from bs4 import BeautifulSoup
from xml.etree import ElementTree as ET

app = FastAPI()


@app.get("/test_crossref")
def test_crossref():
    url = "https://api.crossref.org/works/10.1038/s41586-020-2649-2"  # 安定して取得できるDOI
    headers = {
        "User-Agent": "PubMedGPT/1.0 (mailto:nagoyau.usuda@gmail.com)"  # ←自分の連絡先に変更
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        return {
            "status_code": response.status_code,
            "ok": response.ok,
            "snippet": response.text[:300]  # 応答の冒頭だけ確認
        }
    except Exception as e:
        return {"error": str(e)}

# --------- ウォームアップ用エンドポイント ---------
@app.get("/ping")
def ping():
    return {"status": "ok"}

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
    try:
        headers = {
            "User-Agent": "PubMedGPT/1.0 (mailto:nagoyau.usuda@gmail.com)"
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
    except Exception:
        return {"error": "PubMed検索に失敗しました"}

    pmids = data.get('esearchresult', {}).get('idlist', [])
    results = []

    for pmid in pmids:
        fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        fetch_params = {
            "db": "pubmed",
            "id": pmid,
            "retmode": "xml"
        }
        try:
            fetch_response = requests.get(fetch_url, params=fetch_params, timeout=5)
            if fetch_response.status_code == 200:
                root = ET.fromstring(fetch_response.text)
                title = root.findtext(".//ArticleTitle") or "タイトル取得失敗"
                doi = root.findtext(".//ArticleId[@IdType='doi']")
            else:
                title = "タイトル取得失敗"
                doi = "DOI not found"
        except Exception:
            title = "タイトル取得失敗"
            doi = "DOI not found"

        metadata = get_crossref_metadata(doi) if doi != "DOI not found" else {
            "title": "",
            "authors": [],
            "journal": "",
            "published": [],
            "abstract": "（DOIが見つかりませんでした）"
        }

        results.append({
            "pmid": pmid,
            "title": title,
            "doi": doi,
            "link": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "crossref_metadata": metadata
        })

    biorxiv_papers = get_biorxiv_papers(keyword)
    all_papers = results + biorxiv_papers
    return {"papers": all_papers}

# -------- bioRxiv検索 --------
def get_biorxiv_papers(keyword):
    url = f"https://api.biorxiv.org/details/2022/03/01/{keyword}/json"
    try:
        response = requests.get(url)
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

    doi = doi.strip()
    url = f"https://api.crossref.org/works/{doi}"
    headers = {
        "User-Agent": "PubMedGPT/1.0 (mailto:nagoyau.usuda@gmail.com)"  # ← 自分のメールに変更推奨
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200:
            raise ValueError(f"DOI {doi} returned status {response.status_code}")
        data = response.json().get("message", {})

        # HTML除去（abstract）
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

    except Exception as e:
        print(f"[Crossref ERROR] {doi}: {e}")
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
