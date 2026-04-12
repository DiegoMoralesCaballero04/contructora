"""
MongoDB collection names and helpers.
Three collections:
  - raw_licitaciones: raw HTML/JSON scraped from contratacionesdelestado.es
  - llm_responses:    full Ollama response payloads (before parsing)
  - pdf_chunks:       text chunks extracted from PDFs for LLM processing
"""
from .client import get_db

RAW_LICITACIONES = 'raw_licitaciones'
LLM_RESPONSES = 'llm_responses'
PDF_CHUNKS = 'pdf_chunks'
SCRAPING_LOGS = 'scraping_logs'


def get_collection(name: str):
    return get_db()[name]


def raw_licitaciones():
    return get_collection(RAW_LICITACIONES)


def llm_responses():
    return get_collection(LLM_RESPONSES)


def pdf_chunks():
    return get_collection(PDF_CHUNKS)


def scraping_logs():
    return get_collection(SCRAPING_LOGS)
