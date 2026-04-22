#!/usr/bin/env python3
"""
ShareSub transaction processor from HTML files
Extracts shared subscription data from ShareSub HTML files
and converts it to the same format as the universal transaction processor.
"""

import argparse
import csv
import sys
import os
from bs4 import BeautifulSoup
from datetime import datetime
import re
import requests
import glob
import urllib3

def normalizar_nombre_servicio(nombre_servicio, usuario=None):
    """
    Normalize service names to unify variations.
    Returns the standardized service name.

    Args:
        nombre_servicio: Original service name
        usuario: User/account name (for user-specific rules)
    """
    # User-specific rules
    nombre_limpio = nombre_servicio.strip()

    # user1-specific rule:
    # Audible -> Audible Sky
    if usuario and usuario.lower() == "user1":
        if nombre_limpio.lower() == "audible":
            return "Audible Sky"
        if nombre_limpio.lower() == "movistar plus +":
            return "Movistar+ Sky"
    
    # Service name mapping dictionary (original -> normalized)
    mapeo_servicios = {
        # Amazon
        'Amazon Music': 'Amazon Music Unlimited',
        'Amazon Prime Video pub': 'Amazon Prime Video',
        
        # Atres/Atresmedia
        'ATRESplayer': 'AtresPlayer Premium',
        'Atresplayer Premium Mensual': 'AtresPlayer Premium',
        
        # DAZN
        'Dazn Pro Multihogar': 'DAZN',
        
        # Disney
        'Disney+': 'Disney+ Premium',
        'Disney Standard': 'Disney+ Premium',
        'Disney Standard 🚫📺': 'Disney+ Premium',
        
        # HBO/Max
        'HBO Max': 'HBO Max Premium',
        'Max Premium': 'HBO Max Premium',
        
        # Movistar
        'Movistar Plus': 'Movistar+',
        'Movistar Plus+': 'Movistar+',
        'Movistar Plus +': 'Movistar+',
        
        # Netflix
        'Netflix Premium 🚫📺': 'Netflix Premium',
        
        # NordVPN
        'Nord VPN Estándar': 'NordVPN',
        
        # PureVPN
        'Pure VPN': 'PureVPN',
        
        # Sky
        'SkyShowtime': 'SkyShowtime Premium',
        'SKY SHOWTIME': 'SkyShowtime Premium',
        
        # YouTube
        'YouTube Premium': 'Youtube Premium Family',
        
        # Servicios que mantienen su nombre original
        'Audible': 'Audible',
        'El Mundo': 'El Mundo',
        'Filmin': 'Filmin',
        'Netflix Premium': 'Netflix Premium',
        'PlayStation Plus Premium': 'PlayStation Plus Premium'
    }
    
    # Look up the name in the mapping (case-insensitive)

    # Try exact match first
    if nombre_limpio in mapeo_servicios:
        return mapeo_servicios[nombre_limpio]
    
    # Try case-insensitive match
    for original, normalizado in mapeo_servicios.items():
        if nombre_limpio.lower() == original.lower():
            return normalizado
    
    # Not found — return the cleaned original name
    return nombre_limpio

def detectar_paginas_dashboard_adicionales(archivo_general):
    """
    Auto-detect additional dashboard pages based on the main file name.
    For example, if archivo_general is 'data/sharesub_user1_general.html',
    it will look for 'data/sharesub_user1_general2.html', 'data/sharesub_user1_general3.html', etc.
    """
    archivos_extra = []
    
    # Get the directory and base name of the file
    directorio = os.path.dirname(archivo_general)
    nombre_archivo = os.path.basename(archivo_general)
    
    # Split name and extension
    nombre_sin_ext, extension = os.path.splitext(nombre_archivo)
    
    # Look for files with sequential numbering (2, 3, 4, ...)
    contador = 2
    while True:
        archivo_candidato = os.path.join(directorio, f"{nombre_sin_ext}{contador}{extension}")
        if os.path.exists(archivo_candidato):
            archivos_extra.append(archivo_candidato)
            print(f"📄 Detected additional page: {archivo_candidato}")
            contador += 1
        else:
            break
    
    if archivos_extra:
        print(f"✅ Detected {len(archivos_extra)} additional dashboard pages")
    else:
        print("ℹ️  No additional dashboard pages found")
    
    return archivos_extra

def detectar_archivos_servicios_descargados(archivo_general):
    """
    Auto-detect downloaded service files based on the general dashboard file name.
    For example, if archivo_general is 'data/sharesub_user1_general.html',
    it will look for 'html_descargados/sharesub_user1_sub*.html'
    """
    # Extract the account name from the general file name
    nombre_archivo = os.path.basename(archivo_general)
    
    # Match pattern: sharesub_<account>_general.html -> sharesub_<account>
    match = re.search(r'sharesub_([^_]+)_general\.html', nombre_archivo)
    if match:
        cuenta = match.group(1)
        patron = f"html_descargados/sharesub_{cuenta}_sub*.html"
    else:
        # Fallback: use generic pattern
        patron = "html_descargados/sharesub_*_sub*.html"
    
    archivos_servicios = glob.glob(patron)
    archivos_servicios.sort()  # Sort to keep deterministic order
    
    if archivos_servicios:
        print(f"📁 Detected {len(archivos_servicios)} service files with pattern: {patron}")
        for archivo in archivos_servicios:
            print(f"  📄 {os.path.basename(archivo)}")
    else:
        print(f"⚠️  No service files found with pattern: {patron}")
    
    return archivos_servicios

def obtener_headers_por_cuenta(cuenta_detectada):
    """
    Return HTTP headers specific to the detected account.
    Each account may use a different browser and configuration.
    """
    if cuenta_detectada == "user1":
        # user1 headers — Brave browser with Privacy features
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'es,es-ES;q=1.0',
            'Connection': 'keep-alive',
            'Host': 'www.sharesub.com',
            'Referer': 'https://www.sharesub.com/es/suscripciones',  # Spanish
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Sec-GPC': '1',  # Brave Global Privacy Control
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Brave";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
    elif cuenta_detectada == "user2":
        # user2-specific headers
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9,es-ES;q=0.8,es;q=0.7,fr;q=0.6',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Host': 'www.sharesub.com',
            'Referer': 'https://www.sharesub.com/en/my-shared-subscriptions',  # English
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
    else:
        # Default headers — Microsoft Edge (most universal)
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'es,es-ES;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'DNT': '1',
            'Host': 'www.sharesub.com',
            'Referer': 'https://www.sharesub.com/es/suscripciones',  # Spanish
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 Edg/141.0.0.0',
            'sec-ch-ua': '"Microsoft Edge";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }

def descargar_dashboards_automatico(cuenta, cookies, token=None):
    """
    Automatically download ShareSub dashboard pages.
    Iterates https://www.sharesub.com/es/my-shared-subscriptions?page=N
    and stops when a page contains no active subscriptions.
    Returns a list of paths to the downloaded files.
    """
    MENSAJE_VACIO = "Aún no has compartido ninguna suscripción"  # ShareSub empty-page marker, keep original language for matching

    headers = obtener_headers_por_cuenta(cuenta.lower())
    # Remove Accept-Encoding so requests negotiates only encodings it can safely decompress.
    # If br/zstd is kept, the server may return Brotli/Zstandard and requests may expose raw bytes.
    headers.pop('Accept-Encoding', None)
    if token:
        headers['Authorization'] = f'Bearer {token}'
    headers['Cookie'] = cookies

    os.makedirs('data', exist_ok=True)
    archivos_descargados = []

    for page in range(1, 10):  # maximum 9 pages for safety
        url = f"https://www.sharesub.com/es/my-shared-subscriptions?page={page}"
        print(f"📥 Downloading dashboard page {page}: {url}")
        try:
            resp = requests.get(url, headers=headers, verify=False)

            if resp.status_code != 200:
                print(f"❌ Error {resp.status_code} while downloading dashboard page {page}")
                break

            # Detect if the page is empty (no subscriptions)
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.find_all('div', class_='subscriptions-item')
            pagina_vacia = (
                soup.find('p', class_='subscriptions-items-no-item') is not None
                or MENSAJE_VACIO in resp.text
            )

            if not items or pagina_vacia:
                if page == 1:
                    # Diagnostics: show page title and final URL (after redirects)
                    titulo = soup.find('title')
                    titulo_str = titulo.get_text(strip=True) if titulo else "(no title)"
                    url_final = resp.url if hasattr(resp, 'url') else url
                    print(f"❌ No subscriptions found on page 1.")
                    print(f"   Response title: {titulo_str}")
                    print(f"   Final URL (after redirects): {url_final}")
                    print(f"   Response size: {len(resp.text)} bytes")
                    # Does it look like a login page?
                    if any(kw in resp.text.lower() for kw in ['login', 'iniciar sesión', 'sign in', 'password', 'contraseña']):
                        print(f"   ⚠️  The response appears to be a login page. Cookies may have expired.")
                    else:
                        print(f"   ⚠️  The page loaded but contains no subscriptions. Verify the cookies belong to the correct user.")
                    print(f"   --- First 800 response characters ---")
                    print(resp.text[:800])
                    print(f"   --- End of snippet ---")
                else:
                    print(f"ℹ️  Page {page} with no subscriptions. Download completed.")
                break

            # Save the downloaded page
            if page == 1:
                nombre_archivo = f"data/sharesub_{cuenta}_general.html"
            else:
                nombre_archivo = f"data/sharesub_{cuenta}_general_{page}.html"

            with open(nombre_archivo, 'w', encoding='utf-8-sig') as f:
                f.write(resp.text)

            print(f"✅ Saved: {nombre_archivo} ({len(items)} subscriptions found)")
            archivos_descargados.append(nombre_archivo)

        except Exception as e:
            print(f"❌ Error downloading dashboard page {page}: {e}")
            break

    if archivos_descargados:
        print(f"✅ {len(archivos_descargados)} dashboard page(s) downloaded")
    else:
        print("❌ Could not download any dashboard page")

    return archivos_descargados

def descargar_html_servicios(archivo_general, fecha, output_prefix="sharesub_user1_sub", cookies=None, token=None, archivos_extra=[]):
    """
    Download the HTML for each subscription starting from the general dashboard and extra pages.
    If no archivos_extra are provided, auto-detects additional dashboard pages.
    """
    # If no extra files were provided, auto-detect them
    if not archivos_extra:
        archivos_extra = detectar_paginas_dashboard_adicionales(archivo_general)
    
    servicios = extraer_datos_dashboard(archivo_general, archivos_extra)
    print(f"Found {len(servicios)} services in the dashboard")

    # Auto-detect account name to select the appropriate headers
    nombre_cuenta_archivo = os.path.basename(archivo_general)
    cuenta_detectada = "default"
    
    match_cuenta = re.search(r'sharesub_([^_]+)_general\.html', nombre_cuenta_archivo)
    if match_cuenta:
        cuenta_detectada = match_cuenta.group(1).lower()
    
    # Get account-specific headers
    headers = obtener_headers_por_cuenta(cuenta_detectada)
    # Remove Accept-Encoding so requests only negotiates gzip/deflate
    headers.pop('Accept-Encoding', None)

    # Show which headers are being used
    sec_ch_ua = headers.get('sec-ch-ua', '')
    if "Brave" in sec_ch_ua:
        navegador = "Brave"
    elif "Microsoft Edge" in sec_ch_ua:
        navegador = "Edge"
    elif "Google Chrome" in sec_ch_ua:
        navegador = "Chrome"
    else:
        navegador = "Unknown"
    
    idioma = "ES" if "es/" in headers.get('Referer', '') else "EN"
    print(f"🌐 Using headers for {cuenta_detectada} ({navegador} Browser, {idioma} interface)")
    
    if token:
        headers['Authorization'] = f'Bearer {token}'
    if cookies:
        headers['Cookie'] = cookies
    else:
        print("⚠️  No cookies provided. Downloads are likely to fail.")

    os.makedirs('html_descargados', exist_ok=True)

    # Clean old files for the same account
    patron_limpieza = f"html_descargados/{output_prefix}*.html"
    archivos_anteriores = glob.glob(patron_limpieza)
    if archivos_anteriores:
        print(f"🧹 Cleaning {len(archivos_anteriores)} old files with pattern {output_prefix}*")
        for archivo in archivos_anteriores:
            try:
                os.remove(archivo)
                print(f"  🗑️  Deleted: {os.path.basename(archivo)}")
            except Exception as e:
                print(f"  ❌ Error deleting {archivo}: {e}")

    for idx, (id_servicio, info) in enumerate(servicios.items(), 1):
        url = f"https://www.sharesub.com/en/my-shared-subscriptions/{id_servicio}?date={fecha}#payments-tab"
        print(f"Downloading {url}")
        try:
            resp = requests.get(url, headers=headers, verify=False)
            # Keep original response text and let the writer handle UTF-8-SIG
            if resp.status_code == 200:
                nombre_archivo = f"html_descargados/{output_prefix}{idx}.html"
                with open(nombre_archivo, 'w', encoding='utf-8-sig') as f:
                    f.write(resp.text)
                print(f"✅ Saved: {nombre_archivo}")
            else:
                print(f"❌ Error {resp.status_code} downloading {url}")
        except Exception as e:
            print(f"❌ Error downloading {url}: {e}")

def extraer_datos_dashboard(archivo_general, archivos_extra=[]):
    """
    Extract basic subscription information from the general dashboard and extra pages
    """
    servicios = {}
    archivos_dashboard = [archivo_general] + archivos_extra
    
    for archivo in archivos_dashboard:
        print(f"📄 Processing dashboard: {archivo}")
        try:
            # Try reading with multiple encodings if utf-8 fails
            contenido = None
            for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(archivo, 'r', encoding=encoding) as f:
                        contenido = f.read()
                    break
                except (UnicodeDecodeError, LookupError):
                    continue
            
            if contenido is None:
                print(f"  ❌ Could not read {archivo} with any encoding")
                continue
            
            soup = BeautifulSoup(contenido, 'html.parser')
            
            # Find subscription elements
            items_suscripcion = soup.find_all('div', class_='subscriptions-item')
            print(f"  Found {len(items_suscripcion)} subscription elements")
            
            for item in items_suscripcion:
                try:
                    # Extract service name
                    nombre_elemento = item.find('div', class_='subscriptions-item-name')
                    if not nombre_elemento:
                        continue
                    
                    nombre_servicio = nombre_elemento.get_text(strip=True)
                    
                    # Extract price
                    precio_elemento = item.find('div', class_='subscriptions-item-price')
                    precio = "0"
                    if precio_elemento:
                        precio_texto = precio_elemento.get_text(strip=True)
                        # Extract numbers from price (e.g. "19,99 €" -> "19.99")
                        precio_match = re.search(r'(\d+(?:[,\.]\d+)?)', precio_texto)
                        if precio_match:
                            precio = precio_match.group(1).replace(',', '.')
                    
                    # Extract creation date
                    fecha_elemento = item.find('div', class_='subscriptions-item-date')
                    fecha_creacion = ""
                    if fecha_elemento:
                        fecha_texto = fecha_elemento.get_text(strip=True)
                        # Match date pattern
                        fecha_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', fecha_texto)
                        if fecha_match:
                            fecha_creacion = fecha_match.group(1)
                    
                    # Extract number of subscribers
                    usuarios_elemento = item.find('div', class_='subscriptions-item-users')
                    num_usuarios = 1  # Default: the owner
                    if usuarios_elemento:
                        usuarios_texto = usuarios_elemento.get_text(strip=True)
                        usuario_match = re.search(r'(\d+)', usuarios_texto)
                        if usuario_match:
                            num_usuarios = int(usuario_match.group(1))
                    
                    # Check if the subscription is cancelled or suspended
                    suspendida = False

                    # Check for data-canceled="true" attribute
                    if item.get('data-canceled') == 'true':
                        suspendida = True
                        print(f"⚠️  Cancelled subscription found (data-canceled): {nombre_servicio}")
                    
                    # Check for style="display:none;"
                    if not suspendida:
                        style_attr = item.get('style', '')
                        if 'display:none' in style_attr.replace(' ', ''):
                            suspendida = True
                            print(f"⚠️  Hidden subscription found (display:none): {nombre_servicio}")
                    
                    # Check traditional status elements
                    if not suspendida:
                        estado_elemento = item.find('div', class_='subscriptions-item-status')
                        if estado_elemento:
                            estado_texto = estado_elemento.get_text(strip=True).lower()
                            if any(palabra in estado_texto for palabra in ['suspendida', 'suspended', 'inactive', 'paused', 'pausada', 'canceled', 'cancelled']):
                                suspendida = True
                                print(f"⚠️  Suspended subscription found: {nombre_servicio} - Status: {estado_texto}")
                    
                    # Also check CSS classes that indicate a suspended state
                    if not suspendida:
                        clases_item = ' '.join(item.get('class', []))
                        if any(clase in clases_item.lower() for clase in ['suspended', 'inactive', 'paused', 'disabled', 'canceled', 'cancelled']):
                            suspendida = True
                            print(f"⚠️  Subscription suspended via CSS class: {nombre_servicio}")
                    
                    # Extract individual service URL only if not suspended
                    if not suspendida:
                        enlace = item.find('a')
                        url_servicio = ""
                        if enlace and enlace.get('href'):
                            url_servicio = enlace.get('href')
                            # Extract service ID from the URL
                            id_match = re.search(r'/([a-z0-9]+)$', url_servicio)
                            if id_match:
                                id_servicio = id_match.group(1)
                                servicios[id_servicio] = {
                                    'nombre': nombre_servicio,
                                    'precio_total': float(precio),
                                    'fecha_creacion': fecha_creacion,
                                    'num_usuarios': num_usuarios,
                                    'url': url_servicio
                                }
                    else:
                        print(f"🚫 Skipping suspended subscription: {nombre_servicio}")
                        
                except Exception as e:
                    print(f"Error processing subscription item: {e}", file=sys.stderr)
                    continue
        
        except Exception as e:
            print(f"Error reading dashboard file {archivo}: {e}", file=sys.stderr)
            continue
    
    print(f"✅ Total active services found: {len(servicios)}")
    return servicios

def extraer_pagos_servicio(archivo_servicio):
    """
    Extract payment information from an individual service file
    """
    pagos = []
    
    try:
        # Try reading with different encodings if UTF-8 fails
        contenido = None
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                with open(archivo_servicio, 'r', encoding=encoding) as f:
                    contenido = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue
        
        if contenido is None:
            print(f"❌ Could not read {archivo_servicio} with any encoding", file=sys.stderr)
            return []
        
        soup = BeautifulSoup(contenido, 'html.parser')
        
        # Look up the service name in the page title
        titulo = soup.find('title')
        nombre_servicio = "Unknown service"
        if titulo:
            nombre_servicio = titulo.get_text(strip=True)
        
        # Find payment elements
        items_pago = soup.find_all('div', class_='payments-item')
        
        for item in items_pago:
            try:
                # Extract payer name
                info_elemento = item.find('div', class_='payments-item-info')
                if not info_elemento:
                    continue
                
                nombre_pagador = info_elemento.get_text(strip=True)
                
                # Extract payment price
                precio_elemento = item.find('div', class_='payments-item-price')
                precio = "0"
                if precio_elemento:
                    precio_texto = precio_elemento.get_text(strip=True)
                    precio_match = re.search(r'(\d+(?:[,\.]\d+)?)', precio_texto)
                    if precio_match:
                        precio = precio_match.group(1).replace(',', '.')
                
                # Extract payment date
                desc_elemento = item.find('div', class_='payments-item-description')
                fecha_pago = ""
                estado = "completado"
                if desc_elemento:
                    desc_texto = desc_elemento.get_text(strip=True)
                    # Find date in the description (YYYY/MM/DD or DD/MM/YYYY format)
                    fecha_match = re.search(r'(\d{4}/\d{1,2}/\d{1,2}|\d{1,2}/\d{1,2}/\d{4})', desc_texto)
                    if fecha_match:
                        fecha_pago = fecha_match.group(1)
                    
                    # Determine payment status
                    if "Paid" in desc_texto or "Pagado" in desc_texto:
                        estado = "completed"
                    elif "Pendiente" in desc_texto or "Pending" in desc_texto:
                        estado = "pending"
                
                if precio and float(precio) > 0:
                    pagos.append({
                        'nombre_servicio': nombre_servicio,
                        'nombre_pagador': nombre_pagador,
                        'precio': float(precio),
                        'fecha': fecha_pago,
                        'estado': estado
                    })
                
            except Exception as e:
                print(f"Error processing payment item: {e}", file=sys.stderr)
                continue
    
    except Exception as e:
        print(f"Error reading service file {archivo_servicio}: {e}", file=sys.stderr)
        return []
    
    return pagos

def convertir_fecha_formato_csv(fecha_str):
    """
    Convert DD/MM/YYYY or YYYY/MM/DD to YYYY-MM-DD for CSV.
    """
    if not fecha_str:
        return ""
    
    try:
        # Try YYYY/MM/DD first
        if re.match(r'\d{4}/\d{1,2}/\d{1,2}', fecha_str):
            fecha_obj = datetime.strptime(fecha_str, "%Y/%m/%d")
        else:
            # DD/MM/YYYY format
            fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y")
        
        # Return YYYY-MM-DD for compatibility
        return fecha_obj.strftime("%Y-%m-%d")
    except:
        return fecha_str

def extraer_año_mes_fecha(fecha_str):
    """
    Extract year, month and formatted date from a date string (supports YYYY/MM/DD and DD/MM/YYYY)
    """
    if not fecha_str:
        return "", "", ""
    
    try:
        # Try YYYY/MM/DD first (format used by ShareSub)
        if re.match(r'\d{4}/\d{1,2}/\d{1,2}', fecha_str):
            fecha_obj = datetime.strptime(fecha_str, "%Y/%m/%d")
        else:
            # DD/MM/YYYY format
            fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y")
        
        año = fecha_obj.strftime("%Y")
        mes = fecha_obj.strftime("%m")
        fecha_formato = fecha_obj.strftime("%Y-%m-%d")
        return año, mes, fecha_formato
    except Exception as e:
        print(f"Error parsing date '{fecha_str}': {e}", file=sys.stderr)
        return "", "", fecha_str

def procesar_archivos_sharesub(archivo_general, archivos_servicios, archivos_extra=[], nombre_cuenta="unknown"):
    """
    Process all ShareSub files and produce data in a unified format
    """
    print(f"Processing ShareSub from {archivo_general}...")
    servicios = extraer_datos_dashboard(archivo_general, archivos_extra)
    print(f"Found {len(servicios)} services in the dashboard")

    todas_transacciones = []
    contador_sub = {}  # Number subscriptions per service

    for archivo_servicio in archivos_servicios:
        if not os.path.exists(archivo_servicio):
            print(f"File not found: {archivo_servicio}", file=sys.stderr)
            continue

        print(f"Processing payments from {archivo_servicio}...")
        pagos = extraer_pagos_servicio(archivo_servicio)

        for pago in pagos:
            nombre_servicio_original = pago['nombre_servicio'].strip()
            nombre_servicio = normalizar_nombre_servicio(nombre_servicio_original, nombre_cuenta)
            if nombre_servicio not in contador_sub:
                contador_sub[nombre_servicio] = 0
            contador_sub[nombre_servicio] += 1

            año, mes, fecha_formato = extraer_año_mes_fecha(pago['fecha'])

            transaccion = {
                'Platform': 'ShareSub',
                'Account': nombre_cuenta,
                'Service': nombre_servicio,
                'Sub': str(contador_sub[nombre_servicio]),
                'Year': año,
                'Month': mes,
                'Date': fecha_formato,
                'Revenue': str(pago['precio']).replace('.', ','),
                'Commission': '',
                'Type': '1',
                'Subscriber': pago['nombre_pagador']
            }
            todas_transacciones.append(transaccion)

    return todas_transacciones

def main():
    parser = argparse.ArgumentParser(description='Process ShareSub HTML files, download service pages, and export transactions')
    parser.add_argument('archivo_general', nargs='?', default=None,
                        help='General dashboard HTML file. Optional when using --auto-dashboard.')
    parser.add_argument('archivos_servicios', nargs='*', help='Individual service HTML files')
    parser.add_argument('-o', '--output', help='Output CSV file (default: out/sharesub_transactions.csv)', default='out/sharesub_transactions.csv')
    parser.add_argument('--download', action='store_true', help='Download service HTML files automatically')
    parser.add_argument('--process', action='store_true',
                        help='Process downloaded files and generate CSV')
    parser.add_argument('--date', help='Target date filter (YYYY-MM-DD)', default=None)
    parser.add_argument('--cookies', help='Cookie header value used for authentication', default=None)
    parser.add_argument('--cookies-file', help='File containing cookies in a single line', default=None)
    parser.add_argument('--user', help='Account/user name used in file names (for example: user1, user2)')
    parser.add_argument('--dashboards-extra', nargs='*', help='Additional dashboard HTML files (page 2, page 3, etc.)', default=[])
    parser.add_argument('--token', help='Optional authentication token', default=None)
    parser.add_argument('--silence-ssl-warning', action='store_true',
                        help='Silence urllib3 InsecureRequestWarning (not recommended)')
    parser.add_argument('--auto-dashboard', action='store_true',
                        help='Download dashboard pages automatically from sharesub.com (no general dashboard file needed)')

    args = parser.parse_args()

    # Optionally silence warnings for unverified HTTPS requests.
    if args.silence_ssl_warning:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Load cookies once; they are required for download and auto-dashboard flows.
    cookies = args.cookies
    if args.cookies_file:
        try:
            with open(args.cookies_file, 'r', encoding='utf-8') as f:
                cookies = f.read().strip()
            print(f"✅ Cookies loaded from {args.cookies_file}")
        except Exception as e:
            print(f"❌ Error reading cookies file: {e}", file=sys.stderr)
            sys.exit(1)

    # Auto-download dashboard pages when requested.
    if args.auto_dashboard:
        if not cookies:
            print("❌ --auto-dashboard requires cookies (--cookies or --cookies-file)", file=sys.stderr)
            sys.exit(1)
        if not args.user:
            print("❌ --auto-dashboard requires --user", file=sys.stderr)
            sys.exit(1)
        archivos_dashboard = descargar_dashboards_automatico(args.user, cookies, token=args.token)
        if not archivos_dashboard:
            sys.exit(1)
        args.archivo_general = archivos_dashboard[0]
        if len(archivos_dashboard) > 1 and not args.dashboards_extra:
            args.dashboards_extra = archivos_dashboard[1:]

    # Reuse the cached dashboard automatically when download is requested without archivo_general.
    if not args.archivo_general and args.download and args.user and not args.auto_dashboard:
        candidato_dashboard = f"data/sharesub_{args.user}_general.html"
        if os.path.exists(candidato_dashboard):
            args.archivo_general = candidato_dashboard
            print(f"ℹ️  Using cached dashboard: {args.archivo_general}")

    # Validate the general dashboard file.
    if not args.archivo_general:
        print("Error: provide general dashboard file or use --auto-dashboard", file=sys.stderr)
        sys.exit(1)

    if not os.path.exists(args.archivo_general):
        print(f"Error: general dashboard file not found: {args.archivo_general}", file=sys.stderr)
        sys.exit(1)

    # Download service pages when requested.
    if args.download:
        if not args.date:
            print("You must provide --date YYYY-MM-DD", file=sys.stderr)
            sys.exit(1)

        if not cookies:
            print("❌ You must provide cookies with --cookies or --cookies-file", file=sys.stderr)
            sys.exit(1)

        # Use the account/user name as the file prefix.
        output_prefix = f"sharesub_{args.user}_sub"

        descargar_html_servicios(args.archivo_general, args.date,
                                output_prefix=output_prefix, cookies=cookies, token=args.token,
                                archivos_extra=args.dashboards_extra)

        if not args.process:
            print("Download completed. Add --process to generate CSV output.")
            sys.exit(0)

    # Auto-dashboard can be used on its own for debugging.
    if args.auto_dashboard and not args.download and not args.process:
        print("Dashboard download completed. Add --process to generate CSV output.")
        sys.exit(0)
    
    # Normal processing
    archivos_servicios = args.archivos_servicios
    
    # Extract account name from the general file for use in the output file name
    nombre_cuenta = "unknown"
    nombre_archivo_general = os.path.basename(args.archivo_general)
    match_cuenta = re.search(r'sharesub_([^_]+)_general\.html', nombre_archivo_general)
    if match_cuenta:
        nombre_cuenta = match_cuenta.group(1)
    
    # If no service files were specified, auto-detect them
    if not archivos_servicios:
        print("🔍 No service files specified, auto-detecting...")
        archivos_servicios = detectar_archivos_servicios_descargados(args.archivo_general)
        
        if not archivos_servicios:
            print("Error: no service files were found. Use --download to fetch them automatically or provide the files manually.", file=sys.stderr)
            sys.exit(1)
    
    try:
        transacciones = procesar_archivos_sharesub(args.archivo_general, archivos_servicios, args.dashboards_extra, nombre_cuenta)
        
        if not transacciones:
            print("No transactions found to process", file=sys.stderr)
            return
        
        # Generate output file name in standardized format
        archivo_salida = args.output
        if args.output == 'out/sharesub_transactions.csv':  # This is the default value
            # Extract year and month from the first transaction for the file name
            if transacciones:
                año = transacciones[0]['Year']
                mes = transacciones[0]['Month']
                archivo_salida = f'out/{año}{mes}_sharesub_{nombre_cuenta}_transactions.csv'
            else:
                archivo_salida = f'out/sharesub_{nombre_cuenta}_transactions.csv'
        
        output_dir = os.path.dirname(archivo_salida)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        with open(archivo_salida, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['Platform', 'Account', 'Service', 'Sub', 'Year', 'Month', 'Date', 'Revenue', 'Commission', 'Type', 'Subscriber']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
            
            writer.writeheader()
            for transaccion in transacciones:
                writer.writerow(transaccion)
        
        print(f"✅ Processing completed: {len(transacciones)} transactions saved in {archivo_salida}")
        
        # Additional summary statistics
        if transacciones:
            primer_transaccion = transacciones[0]
            print(f"📊 Summary: {primer_transaccion['Year']}-{primer_transaccion['Month']} | {primer_transaccion['Platform']} | {primer_transaccion['Account']}")
        
        total_ingresos = sum(float(t['Revenue'].replace(',', '.')) for t in transacciones)
        print(f"💰 Total income: {total_ingresos:.2f}€".replace('.', ','))
        
        servicios_unicos = {}
        for t in transacciones:
            servicio = t['Service']
            if servicio not in servicios_unicos:
                servicios_unicos[servicio] = {'transacciones': 0, 'ingresos': 0}
            servicios_unicos[servicio]['transacciones'] += 1
            servicios_unicos[servicio]['ingresos'] += float(t['Revenue'].replace(',', '.'))
        
        print("\n📋 Summary by service:")
        for servicio, stats in servicios_unicos.items():
            print(f"  {servicio}: {stats['transacciones']} transactions, {stats['ingresos']:.2f}€ income".replace('.', ','))
    
    except Exception as e:
        print(f"Error during processing: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

#python sharesub_processor.py data/sharesub_user1_general.html --download --date 2025-09-01 --cookies-file data/cookies_user1.txt --user user1
#python sharesub_processor.py data/sharesub_user1_general.html