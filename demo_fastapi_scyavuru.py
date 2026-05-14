from fastapi import FastAPI, Query
import uvicorn
from apify_client import ApifyClient
import os
from dotenv import load_dotenv

load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
client = ApifyClient(APIFY_TOKEN)

app = FastAPI(
    title="Scyavuru ADVANCED Intelligence API",
    description="Sistema PROFESSIONALE di estrazione Decision Maker GDO",
    version="3.0.0"
)

@app.get("/search", tags=["Intelligence"])
def search_buyers(
    ruolo: str = Query("Category Manager", description="Es: Buyer, Purchasing Director, Category Manager"),
    azienda: str = Query(None, description="Es: Lidl, Esselunga, Carrefour (Opzionale)"),
    location: str = Query("Italy", description="Es: Italy, Germany, Switzerland"),
    max_profili: int = Query(5, ge=1, le=50, description="Numero di profili da estrarre (max 50)")
):
    """
    Estrae profili LinkedIn reali incrociando Ruolo, Azienda e Località.
    """
    # Costruiamo la query magica unendo i campi
    search_query = ruolo
    if azienda:
        search_query += f" at {azienda}"
    search_query += f" {location}"
    
    print(f"🚀 Avvio ricerca avanzata: {search_query}...")
    
    run_input = {
        "searchQuery": search_query,
        "maxPagesPerQuery": 1,
        "maxItems": max_profili,
        "proxyConfiguration": {"useApifyProxy": True}
    }

    try:
        run = client.actor("harvestapi/linkedin-profile-search").call(run_input=run_input)
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        results = []
        for item in dataset_items:
            nome = item.get("name") or item.get("fullName") or (item.get("firstName", "") + " " + item.get("lastName", ""))
            titolo = item.get("headline") or item.get("occupation")
            
            # Estrazione azienda intelligente
            co_name = item.get("companyName")
            if not co_name and item.get("experience"):
                exp = item.get("experience")
                if isinstance(exp, list) and len(exp) > 0:
                    co_name = exp[0].get("companyName")

            results.append({
                "Nome": nome,
                "Qualifica": titolo,
                "Azienda": co_name if co_name else "Da verificare",
                "LinkedIn": item.get("linkedinUrl") or item.get("url")
            })
            
        return {
            "query_eseguita": search_query,
            "risultati": results
        }
    except Exception as e:
        return {"errore": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
