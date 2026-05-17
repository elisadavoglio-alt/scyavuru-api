from fastapi import FastAPI, Query
import uvicorn
from apify_client import ApifyClient
import os
import re
from dotenv import load_dotenv

load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
client = ApifyClient(APIFY_TOKEN)

app = FastAPI(
    title="Scyavuru ADVANCED Intelligence API",
    description="Sistema PROFESSIONALE di estrazione Decision Maker GDO - v4.0 (Google Engine)",
    version="4.0.0"
)

def parse_linkedin_title(title: str):
    """
    Parsa il titolo Google di un profilo LinkedIn.
    Formato tipico: "Nome Cognome - Ruolo at Azienda | LinkedIn"
    oppure:         "Nome Cognome - Ruolo | LinkedIn"
    """
    # Rimuovi " | LinkedIn" dalla fine
    title = re.sub(r'\s*\|\s*LinkedIn.*$', '', title).strip()

    parts = title.split(' - ', 1)
    nome = parts[0].strip() if parts else "N/D"
    resto = parts[1].strip() if len(parts) > 1 else ""

    # Separa qualifica e azienda con " at " o " presso "
    qualifica = resto
    azienda = "Da verificare"
    for sep in [' at ', ' presso ', ' @ ']:
        if sep in resto:
            qualifica = resto.split(sep)[0].strip()
            azienda = resto.split(sep, 1)[1].strip()
            break

    return nome, qualifica, azienda


@app.get("/search", tags=["Intelligence"])
def search_buyers(
    ruolo: str = Query("Category Manager", description="Es: Buyer, Purchasing Director, Category Manager"),
    azienda: str = Query(None, description="Es: Lidl, Esselunga, Carrefour (Opzionale)"),
    location: str = Query("Italy", description="Es: Italy, Germany, Switzerland"),
    max_profili: int = Query(5, ge=1, le=50, description="Numero di profili da estrarre (max 50)")
):
    """
    Estrae profili LinkedIn reali tramite Google Search (nessun limite di run).
    Motore: Apify Google Search Scraper (ufficiale, gratuito).
    """
    # Costruzione query Google stile "site:linkedin.com/in"
    google_query = f'site:linkedin.com/in "{ruolo}"'
    if azienda:
        google_query += f' "{azienda}"'
    google_query += f' "{location}"'

    print(f"Avvio ricerca Google: {google_query}")

    # Numero di pagine necessarie (10 risultati per pagina)
    pages_needed = max(1, -(-max_profili // 10))

    run_input = {
        "queries": google_query,
        "resultsPerPage": 10,
        "maxPagesPerQuery": pages_needed,
        "languageCode": "",
        "mobileResults": False,
        "includeUnfilteredResults": False,
        "saveHtml": False,
        "saveHtmlToKeyValueStore": False,
    }

    try:
        print("Avvio Google Search Scraper su Apify...")
        run = client.actor("apify/google-search-scraper").call(run_input=run_input)
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

        results = []
        for page in dataset_items:
            organic = page.get("organicResults", [])
            for item in organic:
                url = item.get("url", "")
                # Filtra solo URL di profili LinkedIn validi
                if "linkedin.com/in/" not in url:
                    continue

                title = item.get("title", "")
                description = item.get("description", "")

                nome, qualifica, co_name = parse_linkedin_title(title)

                results.append({
                    "Nome": nome,
                    "Qualifica": qualifica,
                    "Azienda": co_name,
                    "LinkedIn": url,
                    "Anteprima": description[:120] if description else ""
                })

                if len(results) >= max_profili:
                    break
            if len(results) >= max_profili:
                break

        return {
            "query_eseguita": google_query,
            "totale_trovati": len(results),
            "risultati": results
        }

    except Exception as e:
        return {"errore": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
