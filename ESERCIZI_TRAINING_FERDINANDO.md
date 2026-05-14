# 🎯 ESERCIZI DI TRAINING PER FERDINANDO (Progetto Scyavuru)

In qualità di Tutor del progetto, ecco i task che Ferdinando deve completare entro mercoledì per validare la sua comprensione del sistema e preparare il passaggio al Cloud.

### ESERCIZIO 1: Ottimizzazione dei Filtri (Precisione)
**Obiettivo:** Estrarre 20 contatti specifici per il mercato tedesco.
*   **Task:** Modificare la chiamata API per cercare "Einkaufsleiter" (Direttore Acquisti in tedesco) in "Germany".
*   **Verifica:** Verificare che il campo 'Azienda' estragga correttamente nomi come Edeka, Rewe o Aldi.

### ESERCIZIO 2: Migrazione Ambiente (Security)
**Obiettivo:** Rendere il codice sicuro per il caricamento su GitHub/Cloud.
*   **Task:** Implementare la lettura del token Apify tramite variabili d'ambiente utilizzando la libreria `python-dotenv`. (Il file .env non deve mai essere caricato online!).
*   **Verifica:** Lo script deve girare correttamente senza avere il token scritto "in chiaro" nel codice.

### ESERCIZIO 3: Integrazione FastAPI (The Bridge)
**Obiettivo:** Trasformare lo script in un servizio web.
*   **Task:** Creare un endpoint `/scrape` che accetti due parametri: `ruolo` e `nazione`. 
*   **Verifica:** Lanciando lo Swagger, l'utente deve poter digitare "Buyer" e "Switzerland" e ricevere il JSON dei risultati.

### ESERCIZIO 4: Analisi dei Trend (Fase 2)
**Obiettivo:** Estrazione di dati testuali dai Post.
*   **Task:** Identificare un Actor su Apify capace di estrarre i post di LinkedIn basandosi su hashtag come #GDO o #FoodInnovation.
*   **Verifica:** Generare una lista grezza di 10 post recenti in un file di testo.

---

**Nota per Ferdinando:** Durante la revisione di mercoledì, discuteremo le scelte degli Actor e la gestione dei limiti di velocità (rate limiting) di LinkedIn.
