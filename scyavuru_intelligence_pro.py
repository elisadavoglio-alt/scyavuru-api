import os
import pandas as pd
from apify_client import ApifyClient
from datetime import datetime
from dotenv import load_dotenv

# Caricamento configurazioni dal file .env (Standard Professionale)
load_dotenv()
APIFY_TOKEN = os.getenv("APIFY_TOKEN")

if not APIFY_TOKEN:
    print("❌ ERRORE: APIFY_TOKEN non trovato nel file .env!")
    exit()

client = ApifyClient(APIFY_TOKEN)

def scyavuru_intelligence_pro(query="Buyer GDO Food", location="Italy", max_items=20):
    """
    Motore di Intelligence Scyavuru v3.0 - Cloud Ready
    """
    print(f"\n--- SCYAVURU INTELLIGENCE START ({datetime.now().strftime('%H:%M:%S')}) ---")
    print(f"🎯 Target: {query} | 📍 Area: {location}")

    run_input = {
        "searchQuery": f"{query} {location}",
        "maxPagesPerQuery": 2,
        "maxItems": max_items,
        "proxyConfiguration": {"useApifyProxy": True}
    }

    try:
        # Avvio dell'Actor (Robottino)
        print("🤖 Avvio robottino nel cloud Apify...")
        run = client.actor("harvestapi/linkedin-profile-search").call(run_input=run_input)
        
        # Recupero dati
        print("📥 Download e analisi dei dati...")
        dataset_items = list(client.dataset(run["defaultDatasetId"]).iterate_items())
        
        results = []
        for item in dataset_items:
            # Estrattore intelligente
            nome = item.get("name") or item.get("fullName") or "Privato"
            titolo = item.get("headline") or "N/D"
            
            # Logica di estrazione Azienda avanzata
            azienda = item.get("companyName") or item.get("company")
            if not azienda and item.get("experience"):
                exp = item.get("experience")
                if isinstance(exp, list) and len(exp) > 0:
                    azienda = exp[0].get("companyName") or exp[0].get("company")
            
            # Se ancora non c'è, puliamo dal titolo
            if not azienda and " at " in titolo:
                azienda = titolo.split(" at ")[-1].strip()
            elif not azienda and " presso " in titolo:
                azienda = titolo.split(" presso ")[-1].strip()

            results.append({
                "Data Estrazione": datetime.now().strftime("%Y-%m-%d"),
                "Nome": nome,
                "Qualifica": titolo,
                "Azienda": azienda if azienda else "Da verificare",
                "LinkedIn URL": item.get("linkedinUrl") or item.get("url"),
                "Località": item.get("locationName") or location
            })

        # Creazione Excel
        df = pd.DataFrame(results)
        output_file = f"/Users/elisadavoglio/Desktop/WORK/LISTA_TARGET_BUYER_SCYAVURU.xlsx"
        df.to_excel(output_file, index=False)
        
        print(f"✅ SUCCESSO! Salvati {len(results)} lead profilati.")
        print(f"📂 File pronto: {output_file}\n")
        
    except Exception as e:
        print(f"⚠️ ERRORE CRITICO: {str(e)}")

if __name__ == "__main__":
    # Test di default
    scyavuru_intelligence_pro()
