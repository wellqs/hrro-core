# Setup: Censo Nominal via Google Sheets

Passos manuais (uma vez só) para ativar `python manage.py import_censo_sheets`.

## 1. Criar a Service Account no Google Cloud
1. Acesse https://console.cloud.google.com/ (pode usar um projeto novo ou existente).
2. Ative a **Google Sheets API** (APIs e serviços → Ativar APIs → busque "Google Sheets API").
3. Vá em **IAM e administrador → Contas de serviço → Criar conta de serviço**.
   - Nome: ex. `censo-hrro-reader`.
   - Não precisa dar papel nenhum de projeto (o acesso é dado direto na planilha).
4. Abra a conta de serviço criada → aba **Chaves** → **Adicionar chave → Criar nova chave → JSON**.
   Isso baixa um arquivo `.json`.

## 2. Guardar a credencial no servidor
- Coloque o `.json` baixado em `secrets/censo-sheets-credentials.json` (pasta já ignorada pelo git).
- Ou aponte para outro caminho via variável de ambiente `CENSO_SHEETS_CREDENTIALS_FILE`.

## 3. Compartilhar a planilha com a Service Account
- Abra o `.json` e copie o valor de `client_email` (algo como `censo-hrro-reader@SEU-PROJETO.iam.gserviceaccount.com`).
- Na planilha do Censo Nominal (KANBAN), clique em **Compartilhar** e adicione esse e-mail como **Leitor**.

## 4. Configurar as variáveis de ambiente
- `CENSO_SHEETS_SPREADSHEET_ID`: o trecho da URL da planilha entre `/d/` e `/edit`.
  Ex.: `https://docs.google.com/spreadsheets/d/`**`1AbCdEfGhIjKlMnOpQrStUvWxYz`**`/edit` → use o trecho em negrito.
- `CENSO_SHEETS_TAB_NAME`: nome exato da aba com o censo nominal (ex. `CENSO_NOMINAL`). Se vazio, usa a primeira aba.
- `CENSO_SHEETS_CREDENTIALS_FILE`: opcional, só se não usar o caminho padrão `secrets/censo-sheets-credentials.json`.

## 5. Testar manualmente
```
python manage.py import_censo_sheets --dry-run
```
Se aparecer o resumo de leitos ocupados/vagos, está funcionando. Depois rode sem `--dry-run`
(e com `--sync-hosp` se quiser o comportamento de snapshot diário, igual ao checkbox do upload manual).

## 6. Agendar execução diária (Windows Task Scheduler)
Crie uma tarefa que rode todo dia, por exemplo:
```
schtasks /create /tn "HRRO - Importar Censo Nominal" /tr "\"C:\caminho\para\python.exe\" \"C:\caminho\para\manage.py\" import_censo_sheets --sync-hosp" /sc daily /st 06:00
```
Ajuste o caminho do `python.exe` (o do venv do projeto) e o horário conforme a rotina do NIR.
