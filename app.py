from fastapi import FastAPI, Query

app = FastAPI()

@app.get("/ping")
def ping():
    return {"status": "ok"}

@app.get("/search_papers")
def search_papers(keyword: str = Query(...)):
    return {"keyword_received": keyword}

