from fastapi import FastAPI, Query, UploadFile, File
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
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY")
client = ApifyClient(APIFY_TOKEN)

app = FastAPI(
    title="Scyavuru ADVANCED Intelligence API",
    description="Sistema PROFESSIONALE di estrazione Decision Maker GDO - v6.0 (Excel + Hunter Email)",
    version="6.0.0"
)

# -------------------------------------------------------
# TABELLA DOMINI AZIENDE GDO EUROPEE (sempre aggiornabile)
# -------------------------------------------------------
COMPANY_DOMAINS = {
    # Italia
    "carrefour": "carrefour.it",
    "carrefour italia": "carrefour.it",
    "esselunga": "esselunga.it",
    "lidl": "lidl.it",
    "lidl italia": "lidl.it",
    "conad": "conad.it",
    "coop": "e.coop.it",
    "aldi": "aldi.it",
    "penny": "penny.it",
    "eurospin": "eurospin.it",
    "pam": "pampanorama.it",
    "unes": "unes.it",
    "iper": "iper.it",
    "il viaggiatore goloso": "ilviaggiatoregolosomercato.it",
    "newprinces": "newprincesgroup.com",
    "newprinces group": "newprincesgroup.com",
    "ferrero": "ferrero.com",
    "barilla": "barilla.com",
    "pastificio rana": "rana.it",
    "metro": "metro.it",
    # Germania
    "rewe": "rewe.de",
    "edeka": "edeka.de",
    "kaufland": "kaufland.de",
    "netto": "netto-online.de",
    "penny markt": "penny.de",
    # Francia
    "leclerc": "e.leclerc",
    "auchan": "auchan.fr",
    "intermarché": "intermarche.com",
    # UK
    "tesco": "tesco.com",
    "sainsburys": "sainsburys.co.uk",
    "waitrose": "waitrose.com",
    "asda": "asda.com",
    # Nordics
    "ica": "ica.se",
    "coop sweden": "coop.se",
    "axfood": "axfood.se",
}

# -------------------------------------------------------
# UTILITY: Ricava dominio da nome azienda
# -------------------------------------------------------
def get_domain_from_company(company_name: str) -> str:
    """
    Tenta di ricavare il dominio aziendale dal nome dell'azienda.
    Prima controlla la tabella, poi chiede a Hunter.
    """
    if not company_name or company_name == "Da verificare":
        return None

    # Normalizza il nome per cercarlo nella tabella
    key = company_name.lower().strip()
    # Cerca match parziale nella tabella
    for known_name, domain in COMPANY_DOMAINS.items():
        if known_name in key or key in known_name:
            return domain

    # Fallback: prova a costruire il dominio dal nome pulito
    # es. "Pastificio Rana Spa" -> "rana.com"
    clean = re.sub(r'\b(s\.?p\.?a\.?|s\.?r\.?l\.?|group|italia|gmbh|ltd|inc)\b', '', key, flags=re.IGNORECASE)
    clean = re.sub(r'[^a-z0-9]', '', clean.strip())
    if clean and len(clean) > 3:
        return f"{clean}.com"  # Tentativo generico

    return None


# -------------------------------------------------------
# UTILITY: Trova email con Hunter.io
# -------------------------------------------------------
def get_email_from_hunter(nome: str, azienda: str) -> tuple:
    """
    Usa Hunter.io per trovare l'email di una persona dato nome e azienda.
    Restituisce (email, score) o ("Non trovata", 0)
    """
    if not HUNTER_API_KEY:
        return "Hunter non configurato", 0

    domain = get_domain_from_company(azienda)
    if not domain:
        return "Dominio non trovato", 0

    parts = nome.strip().split(" ", 1)
    first_name = parts[0] if parts else ""
    last_name = parts[1] if len(parts) > 1 else ""

    try:
        response = requests.get(
            "https://api.hunter.io/v2/email-finder",
            params={
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "api_key": HUNTER_API_KEY
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json().get("data", {})
            email = data.get("email", "")
            score = data.get("score", 0)
            return (email if email else "Non trovata", score)
        return "Non trovata", 0
    except Exception:
        return "Errore Hunter", 0


# -------------------------------------------------------
# UTILITY: Parsing titolo LinkedIn da Google
# -------------------------------------------------------
def parse_linkedin_title(title: str):
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
# UTILITY: Motore di ricerca principale (Apify Harvest)
# -------------------------------------------------------
def run_search(ruolo: str, azienda: str, location: str, max_profili: int, cerca_email: bool = False, apify_api_key: str = None):
    token = apify_api_key or APIFY_TOKEN
    if not token:
        raise ValueError("APIFY API Token mancante. Inseriscilo per accedere ai dati di LinkedIn tramite Harvest.")
        
    client = ApifyClient(token)
    google_query = f'site:linkedin.com/in "{ruolo}" "{location}"'
    if azienda:
        google_query = f'site:linkedin.com/in "{ruolo}" "{azienda}" "{location}"'

    run_input_google = {
        "queries": google_query,
        "resultsPerPage": max_profili + 5,
        "maxPagesPerQuery": 1,
        "saveHtml": False,
        "saveHtmlToKeyValueStore": False,
    }
    
    try:
        run_g = client.actor("apify/google-search-scraper").call(run_input=run_input_google)
        items_g = list(client.dataset(run_g["defaultDatasetId"]).iterate_items())
        
        urls = []
        for page in items_g:
            for item in page.get("organicResults", []):
                url = item.get("url", "")
                if "linkedin.com/in/" in url and url not in urls:
                    urls.append(url)
                    
        if not urls:
            return google_query, []

        run_input_harvest = {
            "profileScraperMode": "Profile details no email ($4 per 1k)",
            "queries": urls[:max_profili]
        }
        
        run_h = client.actor("harvestapi/linkedin-profile-scraper").call(run_input=run_input_harvest)
        items_h = list(client.dataset(run_h["defaultDatasetId"]).iterate_items())
        
        results = []
        for p in items_h:
            nome = p.get('firstName', '') + ' ' + p.get('lastName', '')
            qualifica = p.get('headline', 'N/D')
            co_name = p.get('company', 'Da verificare')
            email = p.get('email', 'N/A')
            link = p.get('url', '')
            
            # Hunter enrichment se richiesto
            email_score = 0
            if (not email or email == 'N/A') and cerca_email:
                email_h, score_h = get_email_from_hunter(nome, co_name)
                if score_h > 0 or email_h != "Non trovata":
                    email = email_h
                    email_score = score_h
                
            results.append({
                "Nome": nome.strip(),
                "Qualifica": qualifica,
                "Azienda": co_name,
                "Email": email,
                "Email Score": email_score if cerca_email else "",
                "LinkedIn": link,
                "Anteprima": "Estratto con Apify Harvest Scraper"
            })
            
        return google_query, results
    except Exception as e:
        raise Exception(f"Errore Apify Harvest: {str(e)}")


# -------------------------------------------------------
# ENDPOINT 1: Ricerca JSON
# -------------------------------------------------------
@app.get("/search", tags=["Intelligence"])
def search_buyers(
    ruolo: str = Query("Category Manager", description="Es: Buyer, Purchasing Director, Category Manager"),
    azienda: str = Query(None, description="Es: Lidl, Esselunga, Carrefour (Opzionale)"),
    location: str = Query("Italy", description="Es: Italy, Germany, Switzerland"),
    max_profili: int = Query(5, ge=1, le=50, description="Numero di profili da estrarre (max 50)"),
    cerca_email: bool = Query(False, description="Attiva ricerca email via Hunter.io (usa crediti)"),
    apify_api_key: str = Query(None, description="La tua API Token di Apify (es. apify_api_...) per usare Harvest")
):
    """
    Estrae profili LinkedIn reali tramite Harvest. Restituisce JSON.
    Per scaricare direttamente un file Excel usa /export
    """
    try:
        google_query, results = run_search(ruolo, azienda, location, max_profili, cerca_email, apify_api_key)
        return {
            "query_eseguita": google_query,
            "totale_trovati": len(results),
            "risultati": results
        }
    except Exception as e:
        return {"errore": str(e)}


# -------------------------------------------------------
# ENDPOINT 2: Export Excel con email Hunter
# -------------------------------------------------------
@app.get("/export", tags=["Intelligence"])
def export_excel(
    ruolo: str = Query("Category Manager", description="Es: Buyer, Purchasing Director, Category Manager"),
    azienda: str = Query(None, description="Es: Lidl, Esselunga, Carrefour (Opzionale)"),
    location: str = Query("Italy", description="Es: Italy, Germany, Switzerland"),
    max_profili: int = Query(10, ge=1, le=50, description="Numero di profili da estrarre (max 50)"),
    cerca_email: bool = Query(False, description="Attiva ricerca email via Hunter.io (usa crediti)"),
    apify_api_key: str = Query(None, description="La tua API Token di Apify (es. apify_api_...) per usare Harvest")
):
    """
    Estrae profili LinkedIn e scarica direttamente un file Excel (.xlsx).
    Attiva cerca_email=true per aggiungere le email tramite Hunter.io.
    """
    try:
        google_query, results = run_search(ruolo, azienda, location, max_profili, cerca_email, apify_api_key)

        df = pd.DataFrame(results)

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


# -------------------------------------------------------
# ENDPOINT 3: Arricchimento CSV (Scyavuru Diretto)
# -------------------------------------------------------
@app.post("/enrich_csv", tags=["Intelligence"])
async def enrich_csv(
    file: UploadFile = File(...),
    cerca_email: bool = Query(True, description="Attiva ricerca email via Hunter.io per i profili caricati")
):
    """
    Carica un file CSV grezzo (estratto via Javascript dal browser) e genera l'Excel perfetto.
    Se cerca_email=True, usa l'intelligenza di Hunter.io per calcolare le email aziendali.
    """
    try:
        content = await file.read()
        # Leggiamo il CSV in un DataFrame Pandas
        df = pd.read_csv(io.BytesIO(content))
        
        results = []
        for index, row in df.iterrows():
            nome = str(row.get("Nome", "")).strip()
            qualifica = str(row.get("Qualifica", "")).strip()
            azienda = str(row.get("Azienda", "")).strip()
            link = str(row.get("Link_LinkedIn", row.get("Link", ""))).strip()
            
            if nome == "nan" or not nome:
                continue
                
            email = str(row.get("Email_Stimata", "Non richiesta"))
            email_score = 0
            if cerca_email:
                email_h, score_h = get_email_from_hunter(nome, azienda)
                if score_h > 0 or email_h != "Non trovata":
                    email = email_h
                    email_score = score_h
                
            results.append({
                "Nome": nome,
                "Qualifica": qualifica,
                "Azienda": azienda,
                "Email": email,
                "Email Score": email_score if cerca_email else "",
                "LinkedIn": link
            })
            
        final_df = pd.DataFrame(results)
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            final_df.to_excel(writer, index=False, sheet_name="Lead Arricchiti")
        output.seek(0)
        
        filename = f"SCYAVURU_LEAD_ARRICCHITI.xlsx"
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        return {"errore": f"Errore durante l'elaborazione del CSV: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
