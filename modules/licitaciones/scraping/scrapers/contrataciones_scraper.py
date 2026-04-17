"""
Scraper for contratacionesdelestado.es (PLACE - Plataforma de Contratación del Sector Público).
Uses the PLACE Atom feed as primary source, falls back to Playwright for HTML scraping.
"""
import logging
import asyncio
import xml.etree.ElementTree as ET
from typing import Optional
import httpx

from .base import BaseScraper

logger = logging.getLogger(__name__)

# PLACE Atom feed — public, no auth, no JS required
PLACE_ATOM_URL = 'https://contrataciondelestado.es/sindicacion/sindicacion_1143/licitacionesPerfilesContratanteCompleto3.atom'

# PLACE HTML search URL (Playwright fallback)
PLACE_SEARCH_URL = (
    'https://contrataciondelestado.es/wps/portal/plataforma/busqueda'
    '?tipoBusqueda=4&estadoLicitacion=ADM&tipoContrato=1&procedimiento=1'
)

DEFAULT_FILTERS = {
    'provincia': 'Valencia',
    'tipo_contrato': '1',     # 1 = Obras
    'procedimiento': '1',     # 1 = Abierto
    'importe_min': 0,
    'importe_max': 4_000_000,
}

# XML namespaces used in PLACE Atom feed
NS = {
    'atom': 'http://www.w3.org/2005/Atom',
    'cac':  'urn:dgpe:names:draft:codice-place-ext:schema:xsd:CommonAggregateComponents-2',
    'cbc':  'urn:dgpe:names:draft:codice:schema:xsd:CommonBasicComponents-2',
    'ns3':  'urn:dgpe:names:draft:codice-place-ext:schema:xsd:MergedNotice-1',
}


class ContratacionesScraper(BaseScraper):
    """
    Scrapes contratacionesdelestado.es for construction tenders.

    Strategy:
    1. Try the PLACE public Atom feed (fast, reliable, no JS).
    2. If Atom fetch fails, fall back to Playwright HTML scraping.
    """

    BASE_URL = 'https://contrataciondelestado.es'

    def __init__(self, filters: dict | None = None, **kwargs):
        super().__init__(**kwargs)
        self.filters = {**DEFAULT_FILTERS, **(filters or {})}

    def scrape(self, max_pages: int = 10) -> list[dict]:
        results = self.run(self._async_scrape(max_pages))
        logger.info('Scraping finished: %d results', len(results))
        return results

    async def _async_scrape(self, max_pages: int) -> list[dict]:
        # Primary: Atom feed
        try:
            results = await self._scrape_via_atom(max_pages)
            if results:
                logger.info('Atom feed returned %d items', len(results))
                return results
            logger.info('Atom feed returned 0 items, trying Playwright')
        except Exception as e:
            logger.warning('Atom feed failed, falling back to Playwright: %s', e)

        # Fallback: Playwright
        await self._start_browser()
        try:
            return await self._scrape_via_playwright(max_pages)
        finally:
            await self._stop_browser()

    # ── Atom feed (primary) ───────────────────────────────────────

    async def _scrape_via_atom(self, max_pages: int) -> list[dict]:
        """Parse the PLACE Atom syndication feed — no JS, reliable."""
        results = []
        max_items = max_pages * 25  # ~25 items per "page"

        browser_headers = {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            ),
            'Accept': 'application/atom+xml, application/xml, text/xml, */*',
            'Accept-Language': 'es-ES,es;q=0.9',
            'Cache-Control': 'no-cache',
        }

        # Try multiple known feed URLs
        feed_urls = [
            PLACE_ATOM_URL,
            'https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteCompleto3.atom',
            'https://contrataciondelestado.es/sindicacion/sindicacion_1143/licitacionesPerfilesContratanteCompleto3.atom',
        ]

        xml_text = None
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            for url in feed_urls:
                try:
                    resp = await client.get(url, headers=browser_headers)
                    resp.raise_for_status()
                    if '<feed' in resp.text or '<rss' in resp.text or '<?xml' in resp.text:
                        xml_text = resp.text
                        logger.info('Atom feed OK from: %s', url)
                        break
                    else:
                        logger.debug('Non-XML response from %s, trying next', url)
                except Exception as e:
                    logger.debug('Feed URL %s failed: %s', url, e)

        if not xml_text:
            raise ValueError('All Atom feed URLs returned non-XML responses')

        root = ET.fromstring(xml_text)
        entries = root.findall('atom:entry', NS)
        logger.info('Atom feed has %d entries', len(entries))

        for entry in entries[:max_items]:
            item = self._parse_atom_entry(entry)
            if item and self._passes_filters(item):
                results.append(item)

        return results

    def _parse_atom_entry(self, entry) -> Optional[dict]:
        """Extract fields from a single Atom <entry> element."""
        try:
            ATOM = 'http://www.w3.org/2005/Atom'

            def atom(tag):
                el = entry.find('{%s}%s' % (ATOM, tag))
                return (el.text or '').strip() if el is not None else ''

            def find_tag(el, tag):
                """Find first element by local tag name in subtree."""
                for child in el.iter():
                    if child.tag.split('}')[-1] == tag:
                        return (child.text or '').strip()
                return ''

            def find_all_tags(el, tag):
                """Find all elements by local tag name."""
                return [(child.text or '').strip()
                        for child in el.iter()
                        if child.tag.split('}')[-1] == tag and child.text]

            # URL: take first link element
            url_origen = ''
            for link_el in entry.findall('{%s}link' % ATOM):
                href = link_el.get('href', '')
                if href:
                    url_origen = href
                    break

            expediente_id = find_tag(entry, 'ContractFolderID')
            if not expediente_id:
                # Fallback: parse from id URL
                id_url = atom('id')
                expediente_id = id_url.split('/')[-1]

            titulo = atom('title') or find_tag(entry, 'Name')

            # Organismo: Party/PartyName/Name (first occurrence)
            organismo = ''
            names = find_all_tags(entry, 'Name')
            # The organismo name is usually the first Name after PartyName
            organismo = names[0] if names else ''

            # Provincia: CountrySubentity (community/province label)
            provincia = find_tag(entry, 'CountrySubentity') or 'N/D'

            # City for municipio — CityName is the organism's address (often Madrid for
            # national bodies), so only use it when it matches the province/region.
            # We try DeliveryAddress CityName first; fall back to empty to avoid misleading data.
            city_raw = find_tag(entry, 'CityName') or ''
            # If the city is Madrid but the province is not a Madrid region, discard it
            # (it's the organism headquarters, not the execution location)
            madrid_regions = {'madrid', 'comunidad de madrid', 'madrid (comunidad de)'}
            province_lower = provincia.lower()
            city_lower = city_raw.lower()
            if city_lower == 'madrid' and not any(m in province_lower for m in madrid_regions):
                municipio = ''
            else:
                municipio = city_raw

            # Importe: TaxExclusiveAmount = presupuesto base sin IVA
            importe_base_raw = find_tag(entry, 'TaxExclusiveAmount')
            if not importe_base_raw:
                importe_base_raw = find_tag(entry, 'EstimatedOverallContractAmount')
            # Last resort: parse from summary "Importe: XXXX EUR"
            if not importe_base_raw:
                import re
                summary = atom('summary')
                m = re.search(r'Importe:\s*([\d.,]+)', summary)
                if m:
                    importe_base_raw = m.group(1)

            importe_iva_raw = find_tag(entry, 'TotalAmount')

            # Dates
            fecha_pub = atom('updated') or atom('published')
            fecha_limite_date = find_tag(entry, 'EndDate')  # TenderingProcess EndDate
            fecha_limite_time = find_tag(entry, 'EndTime')  # TenderingProcess EndTime
            if fecha_limite_date and fecha_limite_time:
                # Combine date + time: "YYYY-MM-DD" + "HH:MM:SS" → "YYYY-MM-DDTHH:MM:SS"
                fecha_limite = f"{fecha_limite_date}T{fecha_limite_time}"
            else:
                fecha_limite = fecha_limite_date or ''

            # Estado PLACE: EV=En Vigor, PU=Publicada, ADJ=Adjudicada, RE=Resuelta...
            estado_place = find_tag(entry, 'ContractFolderStatusCode')

            # CPV
            cpv_codes = find_all_tags(entry, 'ItemClassificationCode')
            cpv = cpv_codes[0] if cpv_codes else ''

            return {
                'expediente_id': expediente_id.strip(),
                'titulo': titulo[:1000],
                'url_origen': url_origen,
                'organismo_nombre': organismo[:500],
                'provincia': provincia[:100],
                'municipio': municipio[:200],
                'importe_base': self._parse_decimal(importe_base_raw),
                'importe_iva': self._parse_decimal(importe_iva_raw),
                'procedimiento': 'ABIERTO',
                'fecha_publicacion': fecha_pub[:19] if fecha_pub else '',
                'fecha_limite_oferta': fecha_limite[:19] if fecha_limite else '',
                'pdf_pliego_url': '',
                'fuente': 'atom',
                'raw_data': {'estado_place': estado_place, 'cpv': cpv},
            }
        except Exception as e:
            logger.debug('Atom entry parse failed: %s', e)
            return None

    def _passes_filters(self, item: dict) -> bool:
        """Apply importe_max filter (province filter is less reliable from Atom)."""
        importe = item.get('importe_base')
        importe_max = self.filters.get('importe_max', 4_000_000)
        importe_min = self.filters.get('importe_min', 0)
        if importe is not None:
            if importe > importe_max or importe < importe_min:
                return False
        return True

    # ── Playwright fallback ───────────────────────────────────────

    async def _scrape_via_playwright(self, max_pages: int) -> list[dict]:
        """Fallback HTML scraping using Playwright."""
        page = await self.new_page()
        results = []

        # Set browser-like headers
        await page.set_extra_http_headers({
            'Accept-Language': 'es-ES,es;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

        # Navigate to main portal first to get session cookies
        logger.debug('Playwright: getting session from main page')
        await self.safe_goto(page, 'https://contrataciondelestado.es/wps/portal/plataforma')
        await page.wait_for_load_state('networkidle', timeout=15000)

        # Now navigate to search
        search_url = (
            f'{PLACE_SEARCH_URL}'
            f'&provincia={self.filters.get("provincia", "Valencia")}'
            f'&importeHasta={self.filters.get("importe_max", 4000000)}'
        )
        logger.debug('Playwright navigating to search: %s', search_url)
        await self.safe_goto(page, search_url)
        await page.wait_for_load_state('networkidle', timeout=30000)

        # Accept cookie banner if present
        try:
            await page.click('#cookieAccept, .cookie-accept, [id*="cookie"] button', timeout=3000)
            await asyncio.sleep(1)
        except Exception:
            pass

        # Wait for any meaningful content (broader selector set)
        selectors = [
            '.tableOfBids', '.resultsTable', '#listadoLicitaciones',
            'table.licitaciones', '.resultados-busqueda table',
            '.licitacion-row', '.bid-row',
            'table[summary*="licitacion"], table[summary*="expediente"]',
            '#wpthemeMainContent table tbody tr',
        ]
        selector_str = ', '.join(selectors)

        try:
            await page.wait_for_selector(selector_str, timeout=30000)
        except Exception:
            content = await page.content()
            logger.warning(
                'No result selectors found after 30s. Page snippet:\n%s',
                content[2000:5000]  # Middle section, skip portal header
            )
            return []

        for page_num in range(max_pages):
            logger.debug('Scraping HTML page %d', page_num + 1)
            rows = await page.query_selector_all(
                'tr.licitacion, .bidRow, .tender-row, table.tableOfBids tbody tr, '
                '.resultsTable tbody tr'
            )
            for row in rows:
                item = await self._extract_row(row)
                if item:
                    results.append(item)

            next_btn = await page.query_selector(
                'a.next, .pagination-next, [aria-label="Siguiente"], '
                'a[title="Siguiente"], .paginacion a:last-child'
            )
            if not next_btn:
                break
            await next_btn.click()
            await page.wait_for_load_state('networkidle')
            await asyncio.sleep(1.5)

        return results

    async def _extract_row(self, row) -> Optional[dict]:
        try:
            text = await row.inner_text()
            if not text.strip():
                return None
            link = await row.query_selector('a[href*="licitacion"], a[href*="expediente"]')
            url = ''
            if link:
                url = await link.get_attribute('href') or ''
                if url and not url.startswith('http'):
                    url = self.BASE_URL + url
            return {
                'expediente_id': '',
                'titulo': text.strip()[:500],
                'url_origen': url,
                'organismo_nombre': '',
                'provincia': self.filters.get('provincia', 'Valencia'),
                'municipio': '',
                'importe_base': None,
                'importe_iva': None,
                'procedimiento': 'ABIERTO',
                'fecha_publicacion': '',
                'fecha_limite_oferta': '',
                'pdf_pliego_url': '',
                'fuente': 'playwright',
            }
        except Exception as e:
            logger.debug('Row extraction failed: %s', e)
            return None

    @staticmethod
    def _parse_decimal(value) -> Optional[float]:
        if value is None or value == '':
            return None
        try:
            return float(str(value).replace(',', '.').replace(' ', '').replace('\xa0', ''))
        except (ValueError, TypeError):
            return None
