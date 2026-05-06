"""
Prompt templates for extracting structured data from licitacion plecs.
Keep prompts versioned — document changes and their effect on extraction quality.
"""

# Version 1 — structured extraction prompt
EXTRACTION_PROMPT_V1 = """Analitza el següent text d'un plec de licitació pública espanyola i extreu les dades en format JSON.

IMPORTANT: Respon ÚNICAMENT amb el JSON, sense cap text addicional, sense markdown, sense explicacions.

Camps a extreure:
- objecte: (string) objecte o descripció del contracte
- pressupost_base: (number) import base de licitació en euros, sense IVA
- pressupost_iva: (number) import amb IVA si s'especifica, null si no
- termini_execucio_mesos: (number) termini d'execució en mesos, null si no s'especifica
- termini_execucio_dies: (number) termini d'execució en dies, null si no s'especifica
- data_limit_ofertes: (string) data límit de presentació d'ofertes en format YYYY-MM-DD, null si no s'especifica
- procediment: (string) tipus de procediment (OBERT, RESTRINGIT, NEGOCIAT, SIMPLIFICAT)
- criteris_adjudicacio: (array) llista de criteris amb:
    - nom: (string) nom del criteri
    - puntuacio: (number) puntuació màxima
    - formula: (string) fórmula de càlcul si s'especifica, "" si no
    - es_economic: (boolean) true si és criteri econòmic (preu)
- formula_economica: (string) fórmula completa de puntuació econòmica, "" si no s'especifica
- classificacio_grup: (string) grup de classificació empresarial (ex: "C"), "" si no requereix
- classificacio_subgrup: (string) subgrup (ex: "2"), "" si no requereix
- classificacio_categoria: (string) categoria (ex: "D"), "" si no requereix
- requereix_declaracio_responsable: (boolean) si requereix declaració responsable
- garantia_provisional: (number) import de garantia provisional en euros, null si no s'exigeix
- garantia_definitiva_percentatge: (number) percentatge de garantia definitiva, null si no s'especifica

Text del plec:
{text}

JSON:"""


# Version 2 — with chain-of-thought (better for complex plecs)
EXTRACTION_PROMPT_V2 = """Ets un expert en contractació pública espanyola. Analitza el text del plec i extreu les dades clau.

Primer identifica mentalment els apartats rellevants del plec, després genera el JSON.

Text:
{text}

Extreu EXACTAMENT aquest JSON (sense text addicional):
{{
  "objecte": "",
  "pressupost_base": null,
  "pressupost_iva": null,
  "termini_execucio_mesos": null,
  "termini_execucio_dies": null,
  "data_limit_ofertes": null,
  "procediment": "OBERT",
  "criteris_adjudicacio": [],
  "formula_economica": "",
  "classificacio_grup": "",
  "classificacio_subgrup": "",
  "classificacio_categoria": "",
  "requereix_declaracio_responsable": false,
  "garantia_provisional": null,
  "garantia_definitiva_percentatge": null
}}"""


# Summary prompt — generates a one-paragraph executive summary
SUMMARY_PROMPT = """Genera un resum executiu d'UN PARÀGRAF (màxim 100 paraules) per a la següent licitació pública.

El resum ha de destacar: objecte del contracte, import, termini, i per a quines empreses és adequada.
Utilitza un to professional i concís. Escriu en català.

Licitació:
{text}

Resum:"""


ACTIVE_EXTRACTION_PROMPT = EXTRACTION_PROMPT_V1
