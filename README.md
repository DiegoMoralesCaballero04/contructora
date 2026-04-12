# CONSTRUTECH-IA

Sistema de vigilancia, análisis y gestión de licitaciones públicas de construcción, desarrollado en el marco del programa **Talent PIME Fase II** (IES Eduardo Primo Marqués, curso 2025-2026).

Reduce de 2 horas a 20-30 minutos la revisión diaria manual de [contratacionesdelestado.es](https://contrataciondelestado.es).

---

## Índice

- [Qué hace](#qué-hace)
- [Arquitectura](#arquitectura)
- [Tecnologías](#tecnologías)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Portal web](#portal-web)
- [API REST](#api-rest)
- [Workflows n8n](#workflows-n8n)
- [Bases de datos](#bases-de-datos)

---

## Qué hace

Cada mañana a las 7:00 (de lunes a viernes), el sistema ejecuta automáticamente el siguiente ciclo:

1. **Scraping** — Busca licitaciones nuevas en contratacionesdelestado.es con los filtros configurados (obras, Comunitat Valenciana, procedimiento abierto, importe 0–4 M EUR).
2. **Descarga** — Baja el PDF del pliego de condiciones de cada licitación y lo sube a AWS S3.
3. **Extracción con LLM** — Envía el texto del PDF a Ollama (Llama 3 en local) y extrae de forma estructurada: importe, plazos, criterios de adjudicación, fórmulas de puntuación y clasificación empresarial requerida.
4. **Resumen** — Genera un resumen ejecutivo por cada licitación.
5. **Alertas** — Envía notificaciones por Telegram con las licitaciones relevantes del día.
6. **Portal** — Todo queda accesible en el portal web para revisión, filtrado, gestión interna e informes.

---

## Arquitectura

```
contratacionesdelestado.es
         |
         v  (Playwright / feed PLACE)
  +-----------------+
  |  Celery Worker  |  <-- Celery Beat (cron 07:00)
  |  scrape task    |
  +--------+--------+
           |
     +-----+------+
     |             |
     v             v
PostgreSQL       MongoDB
(estructurado)   (raw HTML/JSON scrapeado)
     |
     v  (si es relevante)
  +-----+
  |  S3 |  <-- PDF del pliego subido
  +--+--+
     |
     v  (Celery Worker: extract task)
  +--------+
  | Ollama |  (Llama 3 local)
  +---+----+
      |
      +---> PostgreSQL  (datos extraídos + resumen)
      +---> MongoDB     (respuesta raw del LLM)
           |
           v
  Telegram  (alertas automáticas)
           |
           v
  +------------------+     +-----+
  | Portal Django    |     | n8n |  (workflows adicionales)
  +------------------+     +-----+
```

---

## Tecnologías

| Componente | Tecnología | Versión |
|---|---|---|
| Backend / Portal | Django + Gunicorn | 4.2 |
| API REST | Django REST Framework | 3.15 |
| Base de datos relacional | PostgreSQL | 16 |
| Base de datos documental | MongoDB | 7 |
| Cola de tareas | Celery + Redis | 5.4 / 7 |
| Almacenamiento de PDFs | AWS S3 | — |
| Scraping web | Python Playwright | 1.47 |
| Modelo de lenguaje (LLM) | Ollama + Llama 3 | local |
| Orquestación de workflows | n8n | latest |
| Proxy | Nginx | alpine |
| Contenedores | Docker Compose | — |

---

## Estructura del proyecto

```
construtech-ia/
├── apps/
│   ├── licitaciones/      # Modelos principales (Licitacion, InformeIntern,
│   │                      # ConfigEmpresa, ContacteProvincial), API, admin
│   ├── rrhh/              # Control de presencia (Fichaje), perfiles de usuario
│   ├── portal/            # Vistas del portal web, mixins de autenticación, URLs
│   ├── scraping/          # Scraper Playwright, tareas Celery, ScrapingJob
│   ├── extraccion/        # Cliente Ollama, extracción PDF, modelo Extraccion
│   ├── alertas/           # Notificaciones Telegram
│   ├── audit/             # Log de acciones de usuario
│   └── api/               # Router DRF, autenticación API key, health check
├── config/
│   ├── settings.py        # Configuración Django
│   ├── celery.py          # Configuración Celery
│   └── urls.py            # URLs raíz
├── docker/
│   ├── django/Dockerfile  # Imagen Django + Playwright (Ubuntu Jammy)
│   └── nginx/             # Proxy inverso
├── locale/
│   ├── es/                # Traducciones español (idioma base)
│   ├── ca/                # Traducciones valenciano/catalán
│   └── en/                # Traducciones inglés
├── mongo/                 # Cliente pymongo y definición de colecciones
├── n8n/workflows/         # Workflows exportados (JSON)
├── storage/               # Helpers AWS S3 y generación de URLs firmadas
├── templates/portal/      # Plantillas HTML del portal
├── docker-compose.yml     # Todos los servicios
├── requirements.txt
├── .env.example           # Plantilla de variables de entorno
└── Makefile               # Atajos de comandos
```

---

## Instalación

### Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y en marcha
- Git

### Paso 1 — Clonar y configurar el entorno

```bash
cd construtech-ia
cp .env.example .env
```

Edita `.env` con un editor de texto y rellena las credenciales. Ver la sección [Configuración](#configuración).

### Paso 2 — Construir y arrancar los contenedores

```bash
docker compose up -d --build
```

La primera vez tarda unos minutos mientras se construye la imagen Django y se descargan las imágenes de PostgreSQL, MongoDB, Redis, Ollama y n8n.

Para desarrollo local, hay un override que usa `runserver` de forma que los cambios de código se reflejan sin reiniciar contenedores:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d django
# o con el Makefile:
make dev
```

### Paso 3 — Ejecutar las migraciones y crear el superusuario

```bash
docker compose exec django python manage.py migrate
docker compose exec django python manage.py createsuperuser
```

### Paso 4 — Descargar el modelo LLM

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

El modelo pesa aproximadamente 2 GB. Para producción se recomienda `llama3:8b` o superior.

### Paso 5 — Verificar que todo funciona

```bash
curl http://localhost:8000/api/v1/health/
```

Respuesta esperada:

```json
{
  "status": "ok",
  "checks": {
    "django": true,
    "s3": true,
    "ollama": true,
    "mongodb": true
  }
}
```

---

## Configuración

Todas las variables de entorno van al fichero `.env`. No subas este fichero a git.

### Variables obligatorias

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DJANGO_SECRET_KEY` | Clave secreta Django | `openssl rand -hex 32` |
| `POSTGRES_PASSWORD` | Contraseña PostgreSQL | — |

### AWS S3

```env
AWS_ACCESS_KEY_ID=ASIA...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...
AWS_STORAGE_BUCKET_NAME=construtech-licitaciones
AWS_S3_REGION_NAME=eu-south-2
```

Las credenciales temporales (SSO GVA) expiran cada pocas horas. Cuando caduquen, copia las nuevas credenciales del portal AWS y reinicia:

```bash
docker compose restart django celery-worker
```

### Telegram

1. Crea un bot con @BotFather y copia el token.
2. Obtén tu Chat ID entrando a `https://api.telegram.org/bot<TOKEN>/getUpdates`.

```env
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_CHAT_ID=987654321
```

### n8n

```env
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=construtech2026
API_KEY=clave_para_autenticar_llamadas_desde_n8n
```

---

## Portal web

Accede en **http://localhost** (a través de Nginx) o **http://localhost:8000** directamente.

El portal está completamente traducido al español, valenciano y inglés. El idioma se cambia desde el selector en la barra lateral.

### Módulos

#### Licitaciones

Lista paginada con filtros por texto, estado, provincia e importe. Vista de detalle con toda la información extraída por el LLM, criterios de adjudicación, visor del pliego PDF en línea y acceso a los informes internos.

Estados posibles de una licitación:

| Estado | Descripción |
|---|---|
| Nueva | Recién scrapeada, pendiente de revisión |
| Revisada | Revisada y procesada por el workflow de n8n |
| En preparación | El equipo está preparando la oferta |
| Presentada | Oferta enviada |
| Adjudicada | El contrato ha sido adjudicado |
| Desierta | La licitación ha quedado desierta |
| Descartada | No se va a presentar oferta |

#### Informes internos

Permite documentar el análisis interno de cada licitación: análisis técnico, puntos fuertes y débiles, observaciones, puntuación del 1 al 10 y recomendación (presentar / descartar / estudiar más).

Para licitaciones en estado Presentada, Adjudicada o Desierta, el informe se archiva automáticamente como PDF en S3 para trazabilidad. El PDF se genera con el mismo contenido que la vista de impresión del portal.

#### Territorios

Configuración de provincias y municipios de interés para la empresa:

- **Provincia principal** — la provincia base de la empresa (marcada con estrella).
- **Provincias favoritas** — otras provincias donde la empresa licita habitualmente.
- **Municipios** — ciudades concretas de interés.

Las licitaciones de los territorios favoritos aparecen destacadas en el dashboard y se pueden filtrar con un clic desde la lista. En el detalle de cada licitación, si la provincia coincide con un favorito, se muestran automáticamente los contactos locales asociados.

#### Contactos provinciales

Directorio de contactos locales por provincia: subcontratistas, proveedores, delegados, técnicos o arquitectos. Información de contacto (teléfono, email), empresa y notas. Acceso directo desde el detalle de cualquier licitación de esa provincia.

#### Control de presencia (Fichaje)

Registro de entradas y salidas diarias. Cada usuario puede ver su historial y editar sus propios fichajes. Los administradores pueden editar el fichaje de cualquier trabajador desde el módulo de RRHH.

#### RRHH

Vista diaria y semanal de todos los fichajes del personal. Resumen de horas trabajadas por trabajador y semana. Gestión del personal activo.

#### Gestión de usuarios

Alta, edición y baja de usuarios. Cada usuario tiene un rol (Administrador, Jefe, Supervisor, Trabajador) que determina qué secciones del portal puede ver.

### Comandos de gestión

```bash
# Forzar un scraping manual
make scrape

# Limpiar municipios con valor incorrecto ("Madrid" en provincias no madrileñas)
docker compose exec django python manage.py fix_municipios --apply

# Ver logs en tiempo real
make logs
```

### Makefile

```bash
make up            # Arrancar todos los servicios
make down          # Detener todos los servicios
make ps            # Estado de los contenedores
make migrate       # Ejecutar migraciones
make shell         # Django shell interactivo
make superuser     # Crear superusuario
make health        # Comprobar el estado de todos los servicios
make ollama-pull   # Descargar el modelo Llama
make db-shell      # Consola PostgreSQL
make mongo-shell   # Consola MongoDB
```

---

## API REST

Documentación interactiva (Swagger): **http://localhost:8000/api/docs/**

### Autenticación

Las peticiones desde n8n deben incluir la cabecera:

```
X-API-KEY: <valor de API_KEY en .env>
```

### Endpoints principales

| Método | URL | Descripción |
|---|---|---|
| `GET` | `/api/v1/licitacions/` | Lista de licitaciones con filtros |
| `GET` | `/api/v1/licitacions/{id}/` | Detalle con extracción LLM |
| `POST` | `/api/v1/licitacions/{id}/marcar-revisada/` | Cambiar estado a Revisada |
| `POST` | `/api/v1/licitacions/{id}/marcar-descartada/` | Cambiar estado a Descartada |
| `GET` | `/api/v1/licitacions/resum-diari/` | Resumen de licitaciones del día |
| `POST` | `/api/v1/scraping/executar/` | Lanzar un job de scraping |
| `GET` | `/api/v1/health/` | Estado de todos los servicios |

### Parámetros de filtrado

```
?estat=NUEVA
?provincia=Valencia
?importe_min=100000&importe_max=2000000
?fecha_desde=2026-01-01
?ordering=-importe_base
?search=escola municipal
```

---

## Workflows n8n

Accede a n8n en **http://localhost:5678**.

Los workflows se encuentran en `n8n/workflows/` y se importan manualmente desde **Settings → Import from file**.

### Workflow principal: Pipeline completo (`construtech_pipeline_complet.json`)

Se ejecuta de lunes a viernes a las **07:00**. Proceso:

1. Consulta via API las licitaciones nuevas del día (estado NUEVA).
2. Para cada licitación (una a una, procesamiento secuencial con SplitInBatches):
   - Prepara el prompt con los datos de la licitación.
   - Envía el prompt a Ollama (Llama 3) para obtener el análisis.
   - Guarda el resultado y marca la licitación como Revisada.
3. Al finalizar el ciclo, envía un resumen por Telegram con las 5 licitaciones más relevantes del día.

El nodo SplitInBatches procesa cada licitación individualmente para evitar saturar el LLM con 30 ítems a la vez.

### Configurar credenciales en n8n

1. En n8n: **Settings → Credentials → New**
2. Tipo: **HTTP Header Auth**
   - Name: `CONSTRUTECH-API`
   - Header Name: `X-API-KEY`
   - Header Value: (el valor de `API_KEY` en `.env`)
3. Para Telegram: **Telegram API** con el token del bot.

El parse mode de los mensajes Telegram es HTML. Los caracteres especiales `&`, `<` y `>` deben escaparse como `&amp;`, `&lt;` y `&gt;`.

---

## Bases de datos

### PostgreSQL — datos estructurados

| Tabla | Contenido |
|---|---|
| `licitaciones_licitacion` | Licitación con todos sus campos |
| `licitaciones_organismo` | Organismos contratantes |
| `licitaciones_criterioadjudicacion` | Criterios de adjudicación por licitación |
| `licitaciones_informeintern` | Informes internos de análisis |
| `licitaciones_configempresa` | Configuración de la empresa (provincias y municipios favoritos) |
| `licitaciones_contacteprovincial` | Directorio de contactos por provincia |
| `extraccion_extraccion` | Resultado de la extracción LLM por licitación |
| `alertas_alertaconfig` | Configuración de alertas por usuario |
| `scraping_scrapingjob` | Historial de jobs de scraping |
| `rrhh_userprofile` | Perfil y rol de cada usuario |
| `rrhh_fichaje` | Registros de entrada/salida del personal |

### MongoDB — datos en bruto

| Colección | Contenido |
|---|---|
| `raw_licitaciones` | JSON/HTML en bruto scrapeados de PLACE |
| `llm_responses` | Respuestas completas del LLM (prompt + respuesta) |
| `pdf_chunks` | Fragmentos de texto extraídos de los PDFs |

### AWS S3

```
s3://<bucket>/plecs/<expediente_id>/plec_<expediente_id>.pdf
s3://<bucket>/informes/<expediente_id>/informe_<pk>.pdf
```

Los PDFs de pliegos se descargan automáticamente durante el scraping. Los PDFs de informes internos se generan mediante Playwright al crear un informe para una licitación en estado Presentada, Adjudicada o Desierta.

---

## Flujo automático completo

```
07:00 -- Celery Beat --> scrape_licitaciones()
                              |
                     +--------v--------+
                     | Por cada nueva  |
                     | licitación:     |
                     +--------+--------+
                              |
              +---------------+---------------+
              v               v               v
      Guarda en          Guarda raw       Descarga
      PostgreSQL         en MongoDB       PDF a S3
              |
              v
      extreure_dades_pdf()
              |
        Extrae texto PDF
              |
        Envía a Ollama
              |
     +--------v--------+
     | Datos extraídos |---> PostgreSQL (Extraccion)
     | Resumen         |---> MongoDB (llm_responses)
     +-----------------+

n8n 07:00 -- SplitInBatches --> Una licitacion a la vez --> Ollama --> Marcar revisada
          +--> Al finalizar: resumen por Telegram
```

---

## Licencia

Copyright (c) 2025-2026 Diego Morales Caballero. Todos los derechos reservados.

Este software es propietario y confidencial. Queda expresamente prohibido, sin autorización escrita previa del autor:

- Usar este software o cualquier parte del mismo con fines laborales, comerciales o profesionales.
- Vender, sublicenciar, alquilar, transferir o distribuir este software o derivados del mismo.
- Modificar, descompilar o crear obras derivadas con fines distintos al uso personal y académico autorizado.

Para cualquier otro uso, contactar con el autor.
