# Scyavuru Intelligence API

Benvenuto nel repository ufficiale del sistema di intelligence per Scyavuru: questo progetto è finalizzato all'estrazione automatizzata e all'analisi dei decision maker nel settore della GDO europea.

## architettura del sistema: i componenti principali
- **demo_fastapi_scyavuru.py**: il cuore dell'applicazione che gestisce le richieste api e il download in formato excel.
- **requirements.txt**: la lista delle dipendenze necessarie per far girare il software correttamente.
- **render.yaml**: il file di configurazione per il deploy automatico sull'infrastruttura cloud.
- **.env**: il file (da creare localmente) per la gestione sicura del token apify.

## istruzioni per l'uso: come iniziare
1.  **installazione**: installare le librerie necessarie tramite il comando `pip install -r requirements.txt`.
2.  **configurazione**: inserire il proprio token apify nel file .env per abilitare l'estrazione reale.
3.  **esecuzione**: lanciare il server con il comando `python demo_fastapi_scyavuru.py` e accedere all'indirizzo localhost per i test.

## roadmap fase 2: evoluzioni previste
- **analisi dei trend**: implementazione di un actor per lo scraping dei post di linkedin.
- **chaining**: collegamento sequenziale di più robottini per l'arricchimento dei dati con email aziendali.

---
**tutor del progetto**: elisa davoglio  
**sviluppatore**: ferdinando
