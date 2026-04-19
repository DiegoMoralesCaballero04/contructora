# CONSTRUTECH-IA

Sistema de vigilancia, análisis y gestión de licitaciones públicas de construcción, desarrollado en el marco del programa **Talent PIME Fase II** (IES Eduardo Primo Marqués, curso 2025-2026).

Automatiza la revisión diaria de [contratacionesdelestado.es](https://contratacionesdelestado.es), reduciendo el tiempo de análisis de 2 horas a menos de 30 minutos.

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

Cada mañana a las 7:00 (lunes a viernes), el sistema ejecuta automáticamente:

1. **Scraping** — Pagina el feed Atom de PLACE (contratacionesdelestado.es) recogiendo hasta 20 páginas × 50 entradas. Aplica los filtros configurados: tipo de contrato, procedimiento, importe mínimo/máximo, provincias y municipios.
2. **Almacenamiento** — Guarda cada licitación en PostgreSQL y el JSON en bruto en MongoDB.
3. **Descarga de pliegos** — Descarga el PDF del pliego de condiciones y lo sube a AWS S3.
4. **Extracción con IA** — Envía el texto del PDF a Ollama (Llama 3 local) y extrae de forma estructurada: importe, plazos, criterios de adjudicación, fórmulas de puntuación y clasificación empresarial requerida.
5. **Resumen** — n8n genera un resumen ejecutivo por cada licitación nueva usando Ollama.
6. **Alertas** — Envía un informe diario por Telegram con las licitaciones más relevantes.
7. **Portal** — Todo queda accesible en el portal web para revisión, filtrado, gestión interna e informes.

---

## Arquitectura

```
contratacionesdelestado.es (feed Atom PLACE)
         |
         v
  +-----------------+
  |  Celery Worker  |  <-- Celery Beat (cron 07:00 L-V)
  |  scrape task    |
  +--------+--------+
           |
     +-----+------+
     |             |
     v             v
PostgreSQL       MongoDB
(estructurado)   (raw JSON scrapeado)
     |
     v
  +-----+
  |  S3 |  <-- PDF del pliego subido
  +--+--+
     |
     v
  +--------+
  | Ollama |  (Llama 3.2 local)
  +---+----+
      |
      +---> PostgreSQL  (datos extraídos + resumen)
      +---> MongoDB     (respuesta raw del LLM)
           |
           v
  +-------+--------+     +-----+
  | Portal Django  |     | n8n |  (pipeline + alertas Telegram)
  +----------------+     +-----+
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
| Modelo de lenguaje (LLM) | Ollama + Llama 3.2:3b | local |
| Orquestación de workflows | n8n | latest |
| Proxy | Nginx | alpine |
| Contenedores | Docker Compose | — |
| Internacionalización | Django i18n (ES / CA / EN) | — |

---

## Estructura del proyecto

```
construtech/
├── apps/
│   ├── api/               Autenticación por API key, health check, router DRF
│   └── portal/            Vistas web, mixins de login, URLs del portal
├── core/
│   ├── audit/             Log de acciones de usuario
│   ├── mongo/             Cliente pymongo, colecciones
│   └── storage/           Helpers AWS S3, generación de URLs presignadas
├── modules/
│   ├── licitaciones/
│   │   ├── licitaciones/  Modelos principales (Licitacion, InformeIntern,
│   │   │                  ConfigEmpresa, ContacteProvincial, ScrapingTemplate)
│   │   ├── scraping/      Scraper Atom feed PLACE, tareas Celery, ScrapingJob
│   │   ├── extraccion/    Cliente Ollama, extracción PDF, modelo Extraccion
│   │   └── alertas/       Notificaciones Telegram y email
│   ├── rrhh/rrhh/         Perfiles de usuario, roles
│   └── fichajes/          Control de presencia (entradas/salidas)
├── config/
│   ├── settings.py        Configuración Django
│   ├── celery.py          Configuración Celery
│   └── urls.py            URLs raíz
├── docker/
│   ├── django/Dockerfile  Imagen Django + Playwright (Ubuntu Jammy)
│   └── nginx/             Proxy inverso
├── locale/
│   ├── es/                Traducciones español (idioma base)
│   ├── ca/                Traducciones valenciano/catalán
│   └── en/                Traducciones inglés
├── n8n/workflows/         Workflows exportados (JSON)
├── templates/portal/      Plantillas HTML del portal
├── docker-compose.yml     Todos los servicios
├── requirements.txt
├── .env.example           Plantilla de variables de entorno
└── Makefile               Atajos de comandos
```

---

## Instalación

### Requisitos previos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado y en marcha
- Git

### Paso 1 — Clonar y configurar el entorno

```bash
cp .env.example .env
```

Edita `.env` con un editor de texto y rellena las credenciales. Ver la sección [Configuración](#configuración).

### Paso 2 — Construir y arrancar los contenedores

```bash
docker compose up -d --build
```

La primera vez tarda unos minutos mientras se construye la imagen Django y se descargan las imágenes de PostgreSQL, MongoDB, Redis, Ollama y n8n.

Para desarrollo local, usa el override que activa el servidor de desarrollo con recarga automática:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d django
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

### Paso 5 — Importar el workflow de n8n

1. Accede a n8n en **http://localhost:5678**.
2. Ve a **Settings → Import from file**.
3. Importa `n8n/workflows/construtech_pipeline_complet.json`.
4. Configura las credenciales (ver sección [Workflows n8n](#workflows-n8n)).

### Paso 6 — Verificar que todo funciona

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
| `API_KEY` | Clave para autenticar llamadas desde n8n | cualquier string seguro |

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
API_KEY=clave_para_autenticar_llamadas_desde_n8n
```

---

## Portal web

Accede en **http://localhost** (a través de Nginx) o **http://localhost:8000** directamente.

El portal está completamente traducido al español, valenciano y inglés. El idioma se cambia desde el selector en la barra lateral.

### Módulos

#### Licitaciones

Lista paginada con filtros por texto, estado y plazo (solo vigentes por defecto). Columnas: expediente, título, organismo, municipio/provincia, importe base, plazo de presentación con días restantes, estado y enlace al informe/PDF.

La paginación permite navegar con los botones primera/anterior/siguiente/última página, o escribir directamente el número de página y pulsar Enter.

Estados posibles de una licitación:

| Estado | Descripción |
|---|---|
| Nueva | Recién scrapeada, pendiente de revisión |
| Revisada | Procesada por el workflow de n8n |
| En preparación | El equipo está preparando la oferta |
| Presentada | Oferta enviada |
| Adjudicada | El contrato ha sido adjudicado |
| Desierta | La licitación ha quedado desierta |
| Descartada | No se va a presentar oferta |

#### Informes internos

Permite documentar el análisis interno de cada licitación: análisis técnico, puntos fuertes y débiles, observaciones, puntuación del 1 al 10 y recomendación (presentar / descartar / estudiar más).

Al crear un informe, se genera automáticamente un PDF via Playwright y se sube a S3. El PDF es accesible desde la columna PDF de la lista de licitaciones.

#### Scraping — Configuración de plantilla

Panel de administración para configurar los filtros del scraping automático:

- **Importe mínimo/máximo** — rango de importes a incluir.
- **Provincias** — selección de provincias a monitorizar.
- **Municipios** — municipios concretos de interés.
- **Tipos de contrato** — obras, servicios, suministros, etc.
- **Procedimientos** — abierto, restringido, negociado, etc.
- **Códigos CPV** — prefijos de categoría (45 = construcción, 71 = arquitectura, etc.).

#### Territorios

Configuración de poblaciones de interés para el usuario:

- **Municipio principal** — la localidad base (marcada con estrella).
- **Favoritos** — otros municipios donde la empresa licita habitualmente.

Las licitaciones de los municipios favoritos aparecen destacadas y se pueden filtrar desde el dashboard.

#### Contactos provinciales

Directorio de contactos locales por provincia: subcontratistas, proveedores, delegados, técnicos. Acceso directo desde el detalle de cualquier licitación de esa provincia.

#### Control de presencia (Fichaje)

Registro de entradas y salidas diarias. Cada usuario puede ver su historial. Los administradores pueden editar el fichaje de cualquier trabajador desde el módulo de RRHH.

#### RRHH

Vista diaria y semanal de todos los fichajes del personal. Resumen de horas trabajadas por trabajador y semana.

#### Gestión de usuarios

Alta, edición y baja de usuarios. Cada usuario tiene un rol (Administrador, Jefe, Supervisor, Trabajador) que determina las secciones accesibles.

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
make dev           # Arrancar en modo desarrollo con recarga automática
```

---

## API REST

Documentación interactiva (Swagger): **http://localhost:8000/api/docs/**

### Autenticación

Las peticiones deben incluir la cabecera:

```
X-API-Key: <valor de API_KEY en .env>
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
?page_size=50
```

---

## Workflows n8n

Accede a n8n en **http://localhost:5678**.

Los workflows se encuentran en `n8n/workflows/` y se importan desde **Settings → Import from file**.

### Workflow principal: Pipeline completo (`construtech_pipeline_complet.json`)

Se ejecuta de lunes a viernes a las **07:00**. Proceso:

1. Llama al endpoint `/api/v1/scraping/executar/` con `max_pagines: 20` (~88 segundos de scraping).
2. Espera **600 segundos** para que el scraping finalice.
3. Consulta las licitaciones en estado NUEVA ordenadas por importe.
4. Para cada licitación (una a una con SplitInBatches):
   - Prepara un prompt con los datos de la licitación.
   - Envía el prompt a Ollama (Llama 3.2:3b) para obtener un resumen ejecutivo.
   - Marca la licitación como Revisada en Django.
5. Al finalizar el ciclo, genera un informe HTML con las 5 licitaciones más relevantes y lo envía por Telegram.
6. Si no hay licitaciones nuevas, envía un mensaje informativo por Telegram.

### Configurar credenciales en n8n

Las llamadas a Django usan la variable de entorno `CONSTRUTECH_API_KEY` (configurada en `docker-compose.yml` como `${API_KEY}`). No se necesita configurar credenciales adicionales en n8n siempre que `N8N_BLOCK_ENV_ACCESS_IN_NODE=false`.

Para Telegram, configura en n8n: **Settings → Credentials → New → Telegram API** con el token del bot. Alternativamente, el nodo usa la variable de entorno `TELEGRAM_BOT_TOKEN`.

---

## Bases de datos

### PostgreSQL — datos estructurados

| Tabla | Contenido |
|---|---|
| `licitaciones_licitacion` | Licitación con todos sus campos |
| `licitaciones_organismo` | Organismos contratantes |
| `licitaciones_criterioadjudicacion` | Criterios de adjudicación por licitación |
| `licitaciones_informeintern` | Informes internos de análisis |
| `licitaciones_configempresa` | Configuración de la empresa |
| `licitaciones_scrapingtemplate` | Plantillas de configuración del scraping |
| `licitaciones_contacteprovincial` | Directorio de contactos por provincia |
| `extraccion_extraccion` | Resultado de la extracción LLM por licitación |
| `alertas_alertaconfig` | Configuración de alertas por usuario |
| `scraping_scrapingjob` | Historial de jobs de scraping |
| `rrhh_userprofile` | Perfil y rol de cada usuario |
| `rrhh_fichaje` | Registros de entrada/salida del personal |

### MongoDB — datos en bruto

| Colección | Contenido |
|---|---|
| `raw_licitaciones` | JSON en bruto scrapeado de PLACE |
| `llm_responses` | Respuestas completas del LLM (prompt + respuesta) |
| `pdf_chunks` | Fragmentos de texto extraídos de los PDFs |

### AWS S3

```
s3://<bucket>/plecs/<expediente_id>/plec_<expediente_id>.pdf   ← PDF del pliego
s3://<bucket>/informes/<expediente_id>/informe_<pk>.pdf        ← PDF del informe interno
```

---

## Flujo automático completo

```
07:00 Celery Beat
  └─> scrape_licitaciones()
        └─> Pagina feed Atom PLACE (20 páginas × 50 entradas)
              └─> Filtra por provincia / importe / procedimiento / CPV
                    └─> Guarda en PostgreSQL + MongoDB
                          └─> Descarga PDF pliego → S3
                                └─> extreure_dades_pdf()
                                      └─> Ollama extrae datos estructurados
                                            └─> Guarda en PostgreSQL (Extraccion)

07:00 n8n Schedule
  └─> POST /api/v1/scraping/executar/ (max_pagines: 20)
        └─> Espera 600s
              └─> GET /api/v1/licitacions/?estado=NUEVA
                    └─> SplitInBatches (una licitación a la vez)
                          └─> Ollama resumen ejecutivo
                                └─> PATCH marcar-revisada
                                      └─> Telegram informe diario
```

---

## Licencia

Copyright (c) 2025-2026 Diego Morales Caballero. Todos los derechos reservados.

Este software es propietario y confidencial. Queda expresamente prohibido, sin autorización escrita previa del autor:

- Usar este software o cualquier parte del mismo con fines laborales, comerciales o profesionales.
- Vender, sublicenciar, alquilar, transferir o distribuir este software o derivados del mismo.
- Modificar, descompilar o crear obras derivadas con fines distintos al uso personal y académico autorizado.

Para cualquier otro uso, contactar con el autor.
