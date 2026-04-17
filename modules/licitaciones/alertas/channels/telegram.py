import logging
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def enviar_telegram(chat_id: str, missatge: str) -> bool:
    """Send a Telegram message via the Bot API."""
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning('TELEGRAM_BOT_TOKEN not configured')
        return False

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json={
                'chat_id': chat_id,
                'text': missatge,
                'parse_mode': 'HTML',
            })
            resp.raise_for_status()
            logger.info('Telegram message sent to chat %s', chat_id)
            return True
    except Exception as e:
        logger.error('Telegram send failed: %s', e)
        return False


def missatge_nova_licitacio(licitacio) -> str:
    importe = f'{float(licitacio.importe_base):,.0f}' if licitacio.importe_base else 'N/D'
    return (
        f'🏗 <b>Nova licitació detectada</b>\n\n'
        f'📋 {licitacio.titulo[:200]}\n'
        f'💰 Import: {importe} EUR\n'
        f'📍 {licitacio.provincia or "N/D"}\n'
        f'⏰ Termini: {licitacio.fecha_limite_oferta or "N/D"}\n'
        f'🔗 {licitacio.url_origen}'
    )


def missatge_resum_diari(licitacions: list, data) -> str:
    lines = [f'📊 <b>Resum diari CONSTRUTECH-IA</b> — {data}']
    lines.append(f'✅ {len(licitacions)} licitacions noves\n')
    for l in licitacions[:10]:  # Max 10 in Telegram
        importe = f'{float(l.importe_base):,.0f}' if l.importe_base else '?'
        lines.append(f'• {l.titulo[:60]}... ({importe} EUR)')
    if len(licitacions) > 10:
        lines.append(f'... i {len(licitacions) - 10} més')
    return '\n'.join(lines)
