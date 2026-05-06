"""
Microsoft Graph API client for calendar integration.
Handles OAuth2 token refresh and calendar event CRUD.

Required env vars:
  MS_CLIENT_ID, MS_CLIENT_SECRET, MS_TENANT_ID, MS_REDIRECT_URI
"""
import logging
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional

import httpx
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

GRAPH_BASE = 'https://graph.microsoft.com/v1.0'
AUTH_BASE = 'https://login.microsoftonline.com'
SCOPES = ['Calendars.ReadWrite', 'offline_access']


class MicrosoftGraphClient:
    def __init__(self, config):
        self.config = config
        self._access_token: Optional[str] = None

    # ── OAuth2 ────────────────────────────────────────────────────────────────

    @classmethod
    def get_auth_url(cls, state: str = '') -> str:
        tenant = getattr(settings, 'MS_TENANT_ID', 'common')
        client_id = getattr(settings, 'MS_CLIENT_ID', '')
        redirect_uri = getattr(settings, 'MS_REDIRECT_URI', '')
        scope = ' '.join(SCOPES)
        return (
            f'{AUTH_BASE}/{tenant}/oauth2/v2.0/authorize'
            f'?client_id={client_id}'
            f'&response_type=code'
            f'&redirect_uri={redirect_uri}'
            f'&scope={scope}'
            f'&state={state}'
        )

    @classmethod
    def exchange_code(cls, code: str) -> dict:
        tenant = getattr(settings, 'MS_TENANT_ID', 'common')
        url = f'{AUTH_BASE}/{tenant}/oauth2/v2.0/token'
        resp = httpx.post(url, data={
            'client_id': getattr(settings, 'MS_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'MS_CLIENT_SECRET', ''),
            'code': code,
            'redirect_uri': getattr(settings, 'MS_REDIRECT_URI', ''),
            'grant_type': 'authorization_code',
        }, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _refresh_token(self):
        tenant = getattr(settings, 'MS_TENANT_ID', 'common')
        url = f'{AUTH_BASE}/{tenant}/oauth2/v2.0/token'
        resp = httpx.post(url, data={
            'client_id': getattr(settings, 'MS_CLIENT_ID', ''),
            'client_secret': getattr(settings, 'MS_CLIENT_SECRET', ''),
            'refresh_token': self.config.ms_refresh_token,
            'grant_type': 'refresh_token',
        }, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        self.config.ms_access_token = data['access_token']
        if 'refresh_token' in data:
            self.config.ms_refresh_token = data['refresh_token']
        expires_in = data.get('expires_in', 3600)
        self.config.ms_token_expiry = timezone.now() + timedelta(seconds=expires_in)
        self.config.save(update_fields=['ms_access_token', 'ms_refresh_token', 'ms_token_expiry'])
        self._access_token = data['access_token']

    def _get_token(self) -> str:
        if self.config.ms_token_expiry and timezone.now() >= self.config.ms_token_expiry:
            self._refresh_token()
        return self.config.ms_access_token

    def _headers(self) -> dict:
        return {
            'Authorization': f'Bearer {self._get_token()}',
            'Content-Type': 'application/json',
        }

    # ── Calendar operations ───────────────────────────────────────────────────

    def list_calendars(self) -> list:
        resp = httpx.get(f'{GRAPH_BASE}/me/calendars', headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json().get('value', [])

    def create_event(self, event_data: dict, calendar_id: Optional[str] = None) -> dict:
        cal = calendar_id or self.config.ms_calendar_id or 'primary'
        if cal == 'primary':
            url = f'{GRAPH_BASE}/me/events'
        else:
            url = f'{GRAPH_BASE}/me/calendars/{cal}/events'
        resp = httpx.post(url, json=event_data, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def update_event(self, ms_event_id: str, event_data: dict) -> dict:
        url = f'{GRAPH_BASE}/me/events/{ms_event_id}'
        resp = httpx.patch(url, json=event_data, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        return resp.json()

    def delete_event(self, ms_event_id: str):
        url = f'{GRAPH_BASE}/me/events/{ms_event_id}'
        resp = httpx.delete(url, headers=self._headers(), timeout=30)
        if resp.status_code not in (204, 404):
            resp.raise_for_status()

    # ── Event payload builders ────────────────────────────────────────────────

    @staticmethod
    def build_event_payload(esdeveniment) -> dict:
        start_str = esdeveniment.inici.strftime('%Y-%m-%dT%H:%M:%S')
        end_str = esdeveniment.fi.strftime('%Y-%m-%dT%H:%M:%S')
        tz = 'Romance Standard Time'

        body = esdeveniment.descripcio or ''
        if esdeveniment.licitacio:
            body += f'\n\nExpedient: {esdeveniment.licitacio.expediente_id}'
            body += f'\nOrganisme: {getattr(esdeveniment.licitacio.organismo, "nom", "")}'

        payload = {
            'subject': eveniment.titol if hasattr(eveniment, 'titol') else '',
            'body': {'contentType': 'text', 'content': body},
            'start': {'dateTime': start_str, 'timeZone': tz},
            'end': {'dateTime': end_str, 'timeZone': tz},
            'isReminderOn': True,
            'reminderMinutesBeforeStart': esdeveniment.recordatori_minuts,
            'showAs': 'busy',
        }
        if esdeveniment.ubicacio:
            payload['location'] = {'displayName': esdeveniment.ubicacio}
        return payload
