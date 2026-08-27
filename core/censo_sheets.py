"""
censo_sheets.py
---------------
Busca o Censo Nominal diretamente da planilha Google Sheets mantida pela
equipe do NIR, autenticando com uma Service Account (a planilha não fica
pública — é compartilhada apenas com o e-mail da service account).

Requer as variáveis de settings:
  CENSO_SHEETS_CREDENTIALS_FILE  - caminho do JSON da service account
  CENSO_SHEETS_SPREADSHEET_ID    - ID da planilha (trecho da URL entre /d/ e /edit)
  CENSO_SHEETS_TAB_GID           - gid da aba (trecho da URL após #gid=; opcional)
  CENSO_SHEETS_TAB_NAME          - nome da aba (opcional, usado se TAB_GID não for definido; default = primeira aba)
"""

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def fetch_censo_rows():
    """
    Autentica na Google Sheets API e retorna todas as linhas (listas de
    strings) da aba configurada, no mesmo formato que csv.reader produziria.
    """
    import gspread
    from google.oauth2.service_account import Credentials

    if not settings.CENSO_SHEETS_SPREADSHEET_ID:
        raise ImproperlyConfigured(
            "CENSO_SHEETS_SPREADSHEET_ID não configurado (veja settings.py / variáveis de ambiente)."
        )

    creds = Credentials.from_service_account_file(
        settings.CENSO_SHEETS_CREDENTIALS_FILE, scopes=SCOPES
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(settings.CENSO_SHEETS_SPREADSHEET_ID)

    if settings.CENSO_SHEETS_TAB_GID:
        worksheet = spreadsheet.get_worksheet_by_id(int(settings.CENSO_SHEETS_TAB_GID))
    elif settings.CENSO_SHEETS_TAB_NAME:
        worksheet = spreadsheet.worksheet(settings.CENSO_SHEETS_TAB_NAME)
    else:
        worksheet = spreadsheet.sheet1

    return worksheet.get_all_values()
