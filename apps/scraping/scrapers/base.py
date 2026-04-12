import logging
import asyncio
from playwright.async_api import async_playwright, Browser, Page

logger = logging.getLogger(__name__)


class BaseScraper:
    """Base class with Playwright setup, retry logic and common utilities."""

    def __init__(self, headless: bool = True, timeout_ms: int = 30000):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._browser: Browser | None = None

    async def _start_browser(self):
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        logger.debug('Browser launched')
        return self._browser

    async def _stop_browser(self):
        if self._browser:
            await self._browser.close()
        if hasattr(self, '_pw'):
            await self._pw.stop()
        logger.debug('Browser closed')

    async def new_page(self) -> Page:
        context = await self._browser.new_context(
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            locale='es-ES',
        )
        page = await context.new_page()
        page.set_default_timeout(self.timeout_ms)
        return page

    async def safe_goto(self, page: Page, url: str, retries: int = 3):
        for attempt in range(retries):
            try:
                await page.goto(url, wait_until='networkidle')
                return
            except Exception as e:
                logger.warning('Goto failed (attempt %d/%d): %s — %s', attempt + 1, retries, url, e)
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2 ** attempt)

    def run(self, coro):
        """Run an async coroutine from synchronous code (Celery tasks)."""
        return asyncio.run(coro)
