# n8n Workflows — CONSTRUTECH-IA

## Credencials a configurar a n8n

### HTTP Header Auth (per a la API Django)
- Nom: `CONSTRUTECH-API`
- Header: `X-API-KEY`
- Valor: (el valor de `API_KEY` del teu `.env`)

### Telegram (opcional)
- Nom: `CONSTRUTECH-Telegram`
- Bot Token: (el valor de `TELEGRAM_BOT_TOKEN` del teu `.env`)

## Workflows

### 1. trigger_scraping.json
Executa el scraping de contratacionesdelestado.es de dilluns a divendres a les 07:00.
Després envia confirmació per Telegram.

**Importació:**
1. A n8n: Settings → Import from file
2. Selecciona `trigger_scraping.json`
3. Configura les credencials HTTP i Telegram
4. Activa el workflow

### 2. resum_diari.json
Genera i envia un resum diari de licitacions a les 08:00 (L-V).
Consulta l'API Django i formata el missatge.

## URLs de la API

- `POST /api/v1/scraping/executar/` — Llança un nou job de scraping
- `GET /api/v1/licitacions/` — Llista licitacions (filtres: estat, provincia, importe_min/max)
- `GET /api/v1/licitacions/{id}/` — Detall d'una licitació
- `GET /api/v1/health/` — Estat dels serveis (Django, S3, Ollama, MongoDB)
