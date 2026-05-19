# Subscription Transactions Processor

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white&labelColor=101010)](https://www.python.org/)
[![Output](https://img.shields.io/badge/Output-CSV%20%7C%20JSON%20%7C%20XLSX-0A7E3F?style=for-the-badge&logo=files&logoColor=white&labelColor=101010)](#-quick-output-preview)
[![Platforms](https://img.shields.io/badge/Platforms-Spliiit%20Together%20Sharingful%20ShareSub-1F6FEB?style=for-the-badge&logo=databricks&logoColor=white&labelColor=101010)](#-supported-platforms)

Herramienta CLI en Python para extraer, normalizar y exportar transacciones de múltiples plataformas de suscripciones compartidas en un formato unificado CSV / Excel
/ JSON.

> Also available in [English](README.md)

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

## Plataformas soportadas

| Plataforma | Método de extracción |
|---|---|
| Spliiit | API REST (autenticación JWT) |
| Together | API REST (JWT desde localStorage) |
| Sharingful | API REST (token) |
| ShareSub | Scraping HTML (cookies de navegador) |

## Características

- Esquema de salida unificado para todas las plataformas
- Exportación multi-formato: CSV (delimitado por punto y coma para Excel europeo), Excel (.xlsx) y JSON
- Agrupación mensual de transacciones con resumen de ingresos por servicio
- Salida automática al directorio `out/`
- Formato decimal europeo (coma como separador)

## Requisitos

- Python 3.9+

```bash
pip install requests beautifulsoup4 lxml pandas openpyxl
```

## Uso

### Spliiit, Together, Sharingful

```bash
python platform_transactions_cli.py --user <tu_usuario>
```

Sigue las instrucciones interactivas para seleccionar la plataforma y autenticarte.

### ShareSub

```bash
# Descargar el dashboard HTML y las páginas de servicio individuales
python sharesub_html_processor.py --download-dashboard --download-services

# Procesar ficheros HTML ya descargados para un mes concreto
python sharesub_html_processor.py --year 2026 --month 5
```

**Autenticación para ShareSub:** inicia sesión en sharesub.com, abre DevTools → pestaña Network, copia el valor completo del header `Cookie` y guárdalo en un fichero
local según las instrucciones del script.

## Requisitos

- Python 3.9+

```bash
pip install requests beautifulsoup4 lxml pandas openpyxl
```

## Uso

### Spliiit, Together, Sharingful

```bash
python platform_transactions_cli.py --user <tu_usuario>
```

Sigue las instrucciones interactivas para seleccionar la plataforma y autenticarte.

### ShareSub

```bash
# Descargar el dashboard HTML y las páginas de servicio individuales
python sharesub_html_processor.py --download-dashboard --download-services

# Procesar ficheros HTML ya descargados para un mes concreto
python sharesub_html_processor.py --year 2026 --month 5
```

## Características

- Esquema de salida unificado para todas las plataformas
- Exportación multi-formato: CSV (delimitado por punto y coma para Excel europeo), Excel (.xlsx) y JSON
- Agrupación mensual de transacciones con resumen de ingresos por servicio
- Salida automática al directorio `out/`
- Formato decimal europeo (coma como separador)

## Requisitos

- Python 3.9+

```bash
pip install requests beautifulsoup4 lxml pandas openpyxl
```

## Uso

### Spliiit, Together, Sharingful

```bash
python platform_transactions_cli.py --user <tu_usuario>
```

Sigue las instrucciones interactivas para seleccionar la plataforma y autenticarte.

### ShareSub

```bash
# Descargar el dashboard HTML y las páginas de servicio individuales
python sharesub_html_processor.py --download-dashboard --download-services

# Procesar ficheros HTML ya descargados para un mes concreto
python sharesub_html_processor.py --year 2026 --month 5
```

**Autenticación para ShareSub:** inicia sesión en sharesub.com, abre DevTools → pestaña Network, copia el valor completo del header `Cookie` y guárdalo en un fichero
local según las instrucciones del script.

## Esquema de salida

Todas las plataformas generan registros con los siguientes campos:

```
Platform | Account | Service | Sub | Year | Month | Date | Revenue | Commission | Type | Subscriber
```

Los ficheros se guardan en `out/` con nombres que incluyen la plataforma, cuenta, año y mes.