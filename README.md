# GammaOption 📊

**Automated SPX 0DTE Gamma Level Analysis for ES Futures Trading**

Sistema professionale per automatizzare l'analisi dei livelli gamma delle opzioni SPX 0DTE (same-day expiration) e la conversione su ES futures, con alert intelligenti e dashboard real-time.

## 🎯 Cosa Fa

Ogni giorno, in automatico:

1. ✅ Legge opzioni SPX (0DTE) da Polygon.io
2. ✅ Calcola supporti/resistenze basati su gamma exposure
3. ✅ Identifica:
   - **Put Wall** (massimo supporto gamma put)
   - **Call Wall** (massima resistenza gamma call)  
   - **Gamma Flip** (punto di transizione long/short gamma)
4. ✅ Calcola spread SPX → ES
5. ✅ Converte tutti i livelli su ES
6. ✅ Genera alert intelligenti condizionali
7. ✅ Dashboard real-time Streamlit

## 🏗️ Architettura

```
[Dati Opzioni SPX] ─┐
                     ├─> [Motore Calcolo Livelli]
[Dati Prezzo SPX] ──┘          │
                                ▼
                        [Spread ES-SPX]
                                ▼
                        [Livelli ES finali]
                                ▼
                [Alert + Dashboard + Log]
```

## 🚀 Quick Start

### 1. Installazione

```powershell
# Clona il repository
cd C:\projects\GammaOption

# Crea virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Installa dipendenze
pip install -r requirements.txt
```

### 2. Configurazione

```powershell
# Copia il file di esempio
copy .env.example .env

# Modifica .env con le tue API keys
notepad .env
```

**Configurazioni richieste:**
- `POLYGON_API_KEY` - La tua chiave API di Polygon.io (obbligatorio)
- `TELEGRAM_BOT_TOKEN` - Token del bot Telegram (opzionale)
- `TELEGRAM_CHAT_ID` - ID della chat Telegram (opzionale)
- `DISCORD_WEBHOOK_URL` - URL webhook Discord (opzionale)

### 3. Utilizzo

#### Analisi Completa (manuale)
```powershell
python main.py analyze
```
Esegue:
- Fetch dati opzioni SPX 0DTE
- Calcolo gamma levels
- Conversione SPX → ES
- Setup alert

#### Quick Update (check prezzi)
```powershell
python main.py update
```
Aggiorna prezzi correnti e verifica alert

#### Automazione (scheduler)
```powershell
python main.py schedule
```
Esegue automaticamente secondo questo orario (CET):

| Orario | Azione |
|--------|--------|
| 13:45 | Carica opzioni SPX |
| 15:30 | Calcola spread ES-SPX |
| 15:31 | Calcola livelli gamma |
| 15:32 | Attiva alert |
| Ogni minuto | Monitora e trigghera alert |
| 22:00 | Salva log giornaliero |

#### Dashboard Streamlit
```powershell
python main.py dashboard
```
Oppure direttamente:
```powershell
streamlit run dashboard.py
```

Apre dashboard interattiva su http://localhost:8501

## 📊 Dashboard Features

- **Prezzi Real-time**: SPX, ES, Spread
- **Regime di Mercato**: Long Gamma / Short Gamma
- **Livelli Chiave**: Put Wall, Call Wall, Gamma Flip su ES
- **Grafico Interattivo**: Visualizzazione livelli vs prezzo corrente
- **Alert Recenti**: Ultimi alert triggherati
- **Auto-refresh**: Aggiornamento automatico ogni 30 secondi

## 🧠 Logica Core

### Calcolo Dealer Gamma

```python
DealerGamma = -OI × Gamma × 100
```

I dealer vendono opzioni (net short), quindi hanno esposizione gamma opposta.

### Identificazione Livelli

- **Put Wall**: Strike con massima gamma put sotto il prezzo corrente
- **Call Wall**: Strike con massima gamma call sopra il prezzo corrente  
- **Gamma Flip**: Dove la gamma netta cambia segno (transizione long/short)

### Regime di Mercato

- **Long Gamma** (prezzo < Gamma Flip): Mean reversion, volatilità minore
- **Short Gamma** (prezzo > Gamma Flip): Trending, volatilità maggiore

### Conversione SPX → ES

```python
Spread = ES_open - SPX_open  # Fisso per la giornata
Livello_ES = Livello_SPX + Spread
```

### Alert Intelligenti

Gli alert si triggherano solo se:
```
|ES - Livello| < 0.5 punti
AND Volume > soglia
AND Velocità verso il livello
```

## 📁 Struttura Progetto

```
GammaOption/
├── main.py              # Entry point principale
├── config.py            # Configurazione
├── data_fetcher.py      # Fetch dati da Polygon.io
├── gamma_engine.py      # Calcolo gamma levels
├── es_converter.py      # Conversione SPX → ES
├── alert_system.py      # Sistema alert intelligenti
├── scheduler.py         # Automazione oraria
├── dashboard.py         # Dashboard Streamlit
├── requirements.txt     # Dipendenze Python
├── .env.example         # Template configurazione
├── .gitignore          
└── README.md

# Directory create automaticamente:
data/                    # Dati CSV e cache
logs/                    # Log applicazione e alert
```

## 🔧 Parametri Configurabili

Nel file `.env`:

- `STRIKE_RANGE_PERCENT` - Range strike da analizzare (default: 1.5%)
- `MIN_VOLUME_THRESHOLD` - Volume minimo opzioni (default: 50)
- `TOP_LEVELS_COUNT` - Numero livelli da mantenere (default: 5)
- `ALERT_DISTANCE_THRESHOLD` - Distanza per alert (default: 0.5 punti)
- `TIMEZONE` - Fuso orario (default: Europe/Rome)

## 📝 Log e Dati

### File Generati

```
data/
├── options_YYYYMMDD_HHMMSS.csv  # Dati opzioni raw
├── latest_levels.json           # Ultimi livelli calcolati
└── daily_spread.json            # Spread giornaliero cached

logs/
├── app_YYYY-MM-DD_HH-MM-SS.log # Log applicazione
├── scheduler_YYYY-MM-DD_HH-MM-SS.log # Log scheduler
├── alerts.jsonl                 # Alert triggherati (JSON Lines)
└── daily_log_YYYYMMDD.json     # Riepilogo giornaliero
```

## 🔔 Canali Alert

### Telegram
```python
# Setup bot Telegram
# 1. Parla con @BotFather per creare bot
# 2. Ottieni token
# 3. Aggiungi bot a chat e ottieni chat_id
```

### Discord
```python
# Setup webhook Discord
# 1. Vai su Server Settings → Integrations → Webhooks
# 2. Crea nuovo webhook
# 3. Copia URL
```

### Email
```python
# Usa Gmail con App Password
# 1. Abilita 2FA su Gmail
# 2. Genera App Password
# 3. Usa quella nel .env
```

## 🎓 Esempio Output

```
=====================================================================
ANALYSIS COMPLETE - SUMMARY
=====================================================================
SPX Price: $5850.25
ES Price: $5852.75
Spread: +2.50
Regime: SHORT_GAMMA

Key Levels (ES):
  PUT_WALL: $5825.50 (SPX: $5823.00)
  CALL_WALL: $5875.75 (SPX: $5873.25)
  GAMMA_FLIP: $5851.00 (SPX: $5848.50)

=====================================================================
```

## 🐛 Troubleshooting

### "No data available"
- Verifica che POLYGON_API_KEY sia configurata
- Controlla che le API limits di Polygon siano sufficienti
- Esegui `python main.py analyze` prima di vedere la dashboard

### "Could not fetch prices"
- Verifica connessione internet
- Controlla che Polygon.io sia raggiungibile
- Verifica che i ticker SPX e ES siano corretti

### Alert non arrivano
- Verifica configurazione Telegram/Discord/Email
- Controlla logs in `logs/` per errori
- Testa manualmente le credenziali

## 📚 Risorse

- [Polygon.io API Docs](https://polygon.io/docs)
- [SpotGamma (reference)](https://spotgamma.com)
- [Options Greeks Explained](https://www.optionsplaybook.com/options-introduction/option-greeks/)

## 🔐 Sicurezza

- ⚠️ **MAI** committare il file `.env` su Git
- Usa variabili d'ambiente per API keys in produzione
- Limita accesso ai log (contengono dati sensibili)

## 📜 License

MIT License - Uso personale e educativo

## 🤝 Contributi

Questo è un progetto personale per trading automatizzato. 

**Disclaimer**: Questo software è fornito "as is" senza garanzie. Il trading comporta rischi. Usa a tuo rischio e pericolo.

## 📧 Supporto

Per problemi o domande, apri una Issue su GitHub.

---

**Made with ❤️ for gamma exposure analysis**
