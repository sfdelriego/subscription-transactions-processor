# Subscription Transaction Extractor 🚀

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=101010)](https://www.python.org/)
[![Output](https://img.shields.io/badge/Output-CSV%20%7C%20JSON%20%7C%20XLSX-0A7E3F?style=for-the-badge&logo=files&logoColor=white&labelColor=101010)](#-quick-output-preview)
[![Platforms](https://img.shields.io/badge/Platforms-Spliiit%20Together%20Sharingful%20ShareSub-1F6FEB?style=for-the-badge&logo=databricks&logoColor=white&labelColor=101010)](#-supported-platforms)

Extract, normalize, and export subscription transactions from multiple platforms into one clean schema.

> If this project saves you time, consider giving it a Star ⭐

## 👀 Quick Output Preview

The first thing you get is ready-to-use CSV/JSON data.

### CSV Example

```csv
Platform;Account;Service;Sub;Year;Month;Date;Revenue;Commission;Type;Subscriber
Spliiit;test;NordVPN;1;2026;01;2026-01-01;1,93;;1;Derik
Spliiit;test;Filmin;1;2026;01;2026-01-02;5,00;;1;Pablo
Spliiit;test;NordVPN;2;2026;01;2026-01-02;1,93;;1;Leo
Spliiit;test;HBO Max;1;2026;01;2026-01-02;4,00;;1;Fran
Spliiit;test;Proton VPN;1;2026;01;2026-01-03;1,00;;1;Andrea
Spliiit;test;Cyber Ghost;1;2026;01;2026-01-04;0,76;;1;Juan David
```

### JSON Example

```json
[
  {
    "Platform": "Spliiit",
    "Account": "user1",
    "Service": "NordVPN",
    "Sub": 1,
    "Year": 2026,
    "Month": "01",
    "Date": "2026-01-01",
    "Revenue": "1,93",
    "Commission": "",
    "Type": 1,
    "Subscriber": "Derik"
  },
  {
    "Platform": "Spliiit",
    "Account": "user1",
    "Service": "Filmin",
    "Sub": 1,
    "Year": 2026,
    "Month": "01",
    "Date": "2026-01-02",
    "Revenue": "5,00",
    "Commission": "",
    "Type": 1,
    "Subscriber": "Pablo"
  },
  {
    "Platform": "Spliiit",
    "Account": "user1",
    "Service": "NordVPN",
    "Sub": 2,
    "Year": 2026,
    "Month": "01",
    "Date": "2026-01-02",
    "Revenue": "1,93",
    "Commission": "",
    "Type": 1,
    "Subscriber": "Leo"
  }
]
```

## ✨ Supported Platforms

- Spliiit
- Together
- Sharingful
- ShareSub

## 🧱 Unified Schema

All processors generate rows with this exact header:

`Platform;Account;Service;Sub;Year;Month;Date;Revenue;Commission;Type;Subscriber`

Export details:
- Delimiter: `;`
- Encoding: `utf-8-sig` (Excel-friendly)
- Output folder: `out/`

## ⚙️ Requirements

- Python 3.9+
- Recommended packages:

```bash
pip install requests beautifulsoup4 lxml pandas openpyxl
```

Notes:
- `pandas` and `openpyxl` are only required for Excel export in `platform_transactions_cli.py`.

## 🧭 Quick Start

### Spliiit / Together / Sharingful (Interactive CLI)

```bash
python platform_transactions_cli.py --user user1
```

What it does:
- Lets you pick a platform
- Requests auth token and month/year when needed
- Processes transactions
- Exports as CSV, Excel, or JSON

### ShareSub (Automated Download + Process)

```bash
python sharesub_html_processor.py \
  --auto-dashboard \
  --download --process --date 2026-04-01 \
  --cookies-file data/cookies_user1.txt \
  --user user1
```

What this does:
- Downloads dashboard pages into `data/`
- Downloads per-service HTML files into `html_descargados/`
- Generates monthly CSV in `out/`

## 🔐 ShareSub Workflow

### 1. Get Cookies

1. Log in at https://www.sharesub.com.
2. Open DevTools -> Network.
3. Reload the page and open any request to `sharesub.com`.
4. Copy the full `Cookie` header value.
5. Save it in a file such as `data/cookies_user1.txt`.

### 2. Reprocess Without Downloading

If dashboard/service HTML files already exist, regenerate CSV only:

```bash
python sharesub_html_processor.py data/sharesub_user1_general.html --user user1
```

### 3. Useful ShareSub Flags

- `--download`: download service HTML pages
- `--process`: process and generate CSV
- `--date YYYY-MM-DD`: target month for payment tabs
- `--dashboards-extra`: additional dashboard files
- `--auto-dashboard`: auto-download dashboard pages
- `--silence-ssl-warning`: hide urllib3 SSL warning messages

## 🪪 Token Notes

- URL-encoded tokens are decoded automatically (`%7C` -> `|`).
- Together requires JWT from `Authorization: Bearer ...` (not a cookie header).
- Together JWT can usually be found in `Application -> Local Storage` under `CapacitorStorage.AuthClient__Session`.

Spliiit important note:
- Spliiit extraction uses `/api/v1/users/wallets/transactions` (settled wallet movements).
- Per-subscription pages can show operational timing that does not match wallet month boundaries.
- For accounting and real collected amounts, use wallet-based export as source of truth.

## 📁 Project Structure

- `platform_transactions_cli.py`: interactive capture and export for Spliiit/Together/Sharingful
- `sharesub_html_processor.py`: ShareSub dashboard/service HTML processing and optional download
- `data/`: source JSON/HTML examples and cookies files
- `html_descargados/`: downloaded ShareSub service HTML files
- `out/`: generated exports

## ️ Common Issues

- `No subscriptions found on page 1`:
  Cookies likely expired or belong to another account.
- SSL warnings in corporate networks:
  Use `--silence-ssl-warning` for cleaner output.
- Empty CSV:
  Check selected month/date and source data availability.
