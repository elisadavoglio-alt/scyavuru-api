from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
import uvicorn
from apify_client import ApifyClient
import os
import re
import io
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")  # Opzionale: aggiungere in Render
client = ApifyClient(APIFY_TOKEN)

app = FastAPI(
    title="Scyavuru ADVANCED Intelligence API",
    description="Sistema PROFESSIONALE di estrazione Decision Maker GDO - v5.0 (Excel + Apollo Email)",
    version="5.0.0"
)

# -------------------------------------------------------
# UTILITY: Parsing titolo LinkedIn da Google
# -------------------------------------------------------
def parse_linkedin_title(title: str):
    """
    Parsa il titolo Google di un profilo LinkedIn.
    Formato tipico: "Nome Cognome - Ruolo at Azienda | LinkedIn"
    """
    title = re.sub(r'\s*\|\s*LinkedIn.*$', '', title).strip()
    parts = title.split(' - ', 1)
    nome = parts[0].strip() if parts else "N/D"
    resto = parts[1].strip() if len(parts) > 1 else ""
    qualifica = resto
    azienda = "Da verificare"
    for sep in [' at ', ' presso ', ' @ ']:
        if sep in resto:
            qualifica = resto.split(sep)[0].strip()
            azienda = resto.split(sep, 1)[1].strip()
            break
    return nome, qualifica, azienda


# -------------------------------------------------------
# UTILITY: Arricchimento email via Apollo.io
# -------------------------------------------------------
def get_email_from_apollo(linkedin_url: str, nome: str = "") -> str:
    """
    Chiama Apollo.io per trovare l'email da un URL LinkedIn.
    Richiede APOLLO_API_KEY nel file .env o nelle variabili Render.
    """
    if not APOLLO_API_KEY:
        return "Apollo non configurato"
    try:
        parts = nome.strip().split(" ", 1)
        first_name = parts[0] if parts else ""
        last_name = parts[1] if len(parts) > 1 else ""
        payload = {
            "api_key": APOLLO_API_KEY,
            "linkedin_url": linkedin_url,
            "first_name": first_name,
            "last_name": last_name,
            "reveal_personal_emails": False,
        }
        response = requests.post(
            "https://api.apollo.io/v1/people/match",
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            person = data.get("person", {})
            email = person.get("email") or ""
            return email if email else "Non trovata"
        return "Non trovata"
    except Exception:
        return "Errore Apollo"


# -------------------------------------------------------
# UTILITY: Motore di ricerca principale
# -------------------------------------------------------
def run_search(ruolo: str, azienda: str, location: str, max_profili: int, cerca_email: bool = False):
    google_query = f'site:linkedin.com/in "{ruolo}"'
    if azienda:
        google_query += f' "{azienda}"'
    google_query += f' "{location}"'

    pages_needed = max(1, -(-max_profili // 10))

    run_input = {
        "queries": google_query,
        "resultsPerPage": 10,
        "maxPagesPerQuery": pages_needed,
        "saveHtml": False,
        "saveHtmlToKeyValueStore": False,
    }

    run = client.actor("apify/google-search-scraper").call(run_input=run_input)
    dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())

    results = []
    for page in dataset_items:
        for item in page.get("organicResults", []):
            url = item.get("url", "")
            if "linkedin.com/in/" not in url:
                continue
            title = item.get("title", "")
            description = item.get("description", "")
            nome, qualifica, co_name = parse_linkedin_title(title)

            email = ""
            if cerca_email:
                email = get_email_from_apollo(url, nome)

            results.append({
                "Nome": nome,
                "Qualifica": qualifica,
                "Azienda": co_name,
                "Email": email if cerca_email else "N/A (usa /export?cerca_email=true)",
                "LinkedIn": url,
                "Anteprima": description[:120] if description else ""
            })

            if len(results) >= max_profili:
                break
        if len(results) >= max_profili:
            break

    return google_query, results


# -------------------------------------------------------
# ENDPOINT 1: Ricerca JSON (come prima)
# -------------------------------------------------------
@app.get("/search", tags=["Intelligence"])
def search_buyers(
    ruolo: str = Query("Category Manager", description="Es: Buyer, Purchasing Director, Category Manager"),
    azienda: str = Query(None, description="Es: Lidl, Esselunga, Carrefour (Opzionale)"),
    location: str = Query("Italy", description="Es: Italy, Germany, Switzerland"),
    max_profili: int = Query(5, ge=1, le=50, description="Numero di profili da estrarre (max 50)"),
    cerca_email: bool = Query(False, description="Attiva arricchimento email via Apollo (richiede APOLLO_API_KEY)")
):
    """
    Estrae profili LinkedIn reali. Restituisce JSON.
    Per scaricare direttamente un file Excel usa /export
    """
    try:
        google_query, results = run_search(ruolo, azienda, location, max_profili, cerca_email)
        return {
            "query_eseguita": google_query,
            "totale_trovati": len(results),
            "risultati": results
        }
    except Exception as e:
        return {"errore": str(e)}


# -------------------------------------------------------
# ENDPOINT 2: Export Excel - SCARICA FILE DIRETTAMENTE
# -------------------------------------------------------
@app.get("/export", tags=["Intelligence"])
def export_excel(
    ruolo: str = Query("Category Manager", description="Es: Buyer, Purchasing Director, Category Manager"),
    azienda: str = Query(None, description="Es: Lidl, Esselunga, Carrefour (Opzionale)"),
    location: str = Query("Italy", description="Es: Italy, Germany, Switzerland"),
    max_profili: int = Query(10, ge=1, le=50, description="Numero di profili da estrarre (max 50)"),
    cerca_email: bool = Query(False, description="Attiva arricchimento email via Apollo (richiede APOLLO_API_KEY)")
):
    """
    Estrae profili LinkedIn e scarica direttamente un file Excel (.xlsx).
    Clicca Execute e poi scarica il file dal link nella risposta.
    """
    try:
        google_query, results = run_search(ruolo, azienda, location, max_profili, cerca_email)

        df = pd.DataFrame(results)

        # Creazione Excel in memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Lead GDO")
        output.seek(0)

        filename = f"SCYAVURU_LEAD_{ruolo.replace(' ', '_')}_{location}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        return {"errore": str(e)}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
