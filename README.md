# Subscription Transaction Extractor

Python tools to capture and normalize transactions from Spliiit, Together, Sharingful, and ShareSub into a unified CSV format.

## Requirements

- Python 3.9+
- Recommended packages:

```bash
pip install requests beautifulsoup4 lxml pandas openpyxl
```

Notes:
- `pandas` and `openpyxl` are only required for Excel export in `script_completo.py`.

## Output Format

All processors generate rows with these columns:

`Plataforma;Usuario;Servicio;Sub;Año;Mes;Fecha;Ingreso;Comision;Tipo;User`

Output details:
- Delimiter: `;`
- Encoding: `utf-8-sig` (Excel-friendly)
- Output folder: `out/`

## ShareSub Workflow

### 1. Get Cookies

1. Log in at https://www.sharesub.com.
2. Open DevTools -> Network.
3. Reload the page and open any request to `sharesub.com`.
4. Copy the full `Cookie` header value.
5. Save it in a file such as `data/cookies_user1.txt`.

### 2. Full Automated Flow

```bash
python sharesub_processor.py \
  --auto-dashboard \
  --download --process --date 2026-04-01 \
  --cookies-file data/cookies_user1.txt \
  --user user1
```

What this does:
- Downloads dashboard pages into `data/`
- Downloads per-service HTML files into `html_descargados/`
- Generates a monthly CSV in `out/`

Run the same flow for `user2` by changing `--cookies-file` and `--user`.

### 3. Reprocess Without Downloading

If dashboard/service HTML files already exist, regenerate CSV only:

```bash
python sharesub_processor.py data/sharesub_user1_general.html --user user1
```

### 4. Useful ShareSub Flags

- `--download`: download service HTML pages
- `--process`: process and generate CSV
- `--date YYYY-MM-DD`: target month for payment tabs
- `--dashboards-extra`: additional dashboard files
- `--auto-dashboard`: auto-download dashboard pages
- `--silence-ssl-warning`: hide urllib3 SSL warning messages

## Spliiit / Together / Sharingful Workflow

### 1. Interactive Capture

```bash
python script_completo.py --user user1
```

The script will:
- Ask which platform to capture
- Ask for authentication token and month/year when needed
- Process transactions
- Export as CSV, Excel, or JSON

Token note:
- If your token was copied from Application/Cookies and contains URL-encoded characters (for example `%7C`), the script now decodes it automatically (`%7C` -> `|`).
- Together requires a JWT from `Authorization: Bearer ...` (not the `Cookie` header). If you paste cookie-like text by mistake, the script now warns and stops with guidance.
- For Together, you can often get the JWT directly from `Application -> Local Storage` under the key `CapacitorStorage.AuthClient__Session`. Its value is usually a JSON object like `{"token":"eyJ..."}`.

Spliiit note (important):
- Spliiit extraction is based on the general wallet endpoint (`/api/v1/users/wallets/transactions`), which represents settled wallet movements.
- The per-subscription page (`/offer/<id>/transactions`) can show operational timing/details that do not always match the same calendar month as the wallet view.
- For accounting and real collected amounts, use the wallet-based export as the source of truth.

### 2. Reprocess Saved JSON Files

```bash
python universal_transaction_processor.py data/spliiit_transactions202509.json
python universal_transaction_processor.py data/together_transactions202509.json
python universal_transaction_processor.py data/sharingful_transactions202509.json
```

The platform is detected automatically from file structure/name.

## Project Structure

- `script_completo.py`: interactive capture and export for Spliiit/Together/Sharingful
- `sharesub_processor.py`: ShareSub dashboard/service HTML processing and optional download
- `universal_transaction_processor.py`: JSON-to-CSV processor for Spliiit/Together/Sharingful
- `spliiit_transactions.py`: minimal Spliiit-only processor
- `data/`: source JSON/HTML examples and cookies files
- `html_descargados/`: downloaded ShareSub service HTML files
- `out/`: generated exports

## Privacy and GitHub Publishing

This repository can contain sensitive files in local runs (cookies, downloaded HTML, personal transaction data).
Before publishing, add at least these paths to `.gitignore`:

```gitignore
data/cookies_*.txt
data/*_transactions*.json
data/sharesub_*_general*.html
html_descargados/
out/
```

Also verify there are no real names, emails, tokens, or cookies in committed files.

## Common Issues

- `No subscriptions found on page 1`:
  - Cookies likely expired or belong to another account.
- SSL warnings in corporate networks:
  - Use `--silence-ssl-warning` for cleaner output.
- Empty CSV:
  - Check selected month/date and source data availability.
