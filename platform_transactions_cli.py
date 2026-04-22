"""Interactive tool to capture, process, and export subscription transactions."""
import argparse
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import unquote
import base64

# ============================================
# PART 1: DATA CAPTURE
# ============================================

def normalizar_token_auth(token_crudo):
    """Normalize token input from browser sources (headers/cookies/application storage)."""
    token = (token_crudo or "").strip().strip('"').strip("'")

    if token.lower().startswith('bearer '):
        token = token[7:].strip()

    token_inicial = token
    for _ in range(2):
        decodificado = unquote(token)
        if decodificado == token:
            break
        token = decodificado

    if token != token_inicial:
        print("ℹ️  URL-encoded token detected and decoded automatically (example: %7C -> |)")

    return token

def extraer_jwt_together(auth_crudo):
    """Extract a Together JWT from raw pasted text (token/header/cookie-like input)."""
    texto = normalizar_token_auth(auth_crudo)
    if not texto:
        return None

    # Try to extract from full header text first.
    bearer_match = re.search(r'authorization\s*:\s*bearer\s+([^\s;]+)', texto, flags=re.IGNORECASE)
    if bearer_match:
        return normalizar_token_auth(bearer_match.group(1))

    # Try to locate a JWT anywhere in the pasted text.
    jwt_match = re.search(r'eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*', texto)
    if jwt_match:
        token_extraido = jwt_match.group(0)
        if token_extraido != texto:
            print("ℹ️  JWT detected inside pasted text and extracted automatically.")
        return token_extraido

    # Cookie/header-like input without JWT is a common mistake.
    if ';' in texto and '=' in texto:
        print("❌ It looks like you pasted a Cookie header, not a JWT token.")
        print("   For Together, copy Authorization: Bearer <JWT> from DevTools -> Network.")
        print("   You can paste only the JWT, or the full Authorization header line.")
        return None

    return texto

def decodificar_jwt_exp(token_jwt):
    """Decode JWT payload and extract exp (expiration) time. Return None if invalid."""
    try:
        partes = token_jwt.split('.')
        if len(partes) < 2:
            return None
        payload_b64 = partes[1]
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding
        payload_json = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_json)
        if 'exp' in payload:
            return payload['exp']
        return None
    except Exception:
        return None

def mostrar_jwt_info(auth_token):
    """Show JWT expiration info if available."""
    exp_ts = decodificar_jwt_exp(auth_token)
    if exp_ts:
        exp_dt = datetime.fromtimestamp(exp_ts)
        now = datetime.now()
        if exp_dt < now:
            print(f"⚠️  JWT has expired (was valid until {exp_dt.strftime('%Y-%m-%d %H:%M:%S')})")
            return False
        remaining = exp_dt - now
        remaining_min = int(remaining.total_seconds() / 60)
        if remaining_min < 5:
            print(f"⚠️  JWT will expire in {remaining_min} minutes")
        else:
            print(f"✅ JWT valid for ~{remaining_min} minutes")
        return True
    return None

def capturar_transacciones_automatico(metodo='api', plataforma='spliiit'):
    """Capture transactions automatically using API or local JSON."""
    if metodo == 'api':
        return capturar_con_api(plataforma)
    elif metodo == 'manual':
        return cargar_desde_archivo()

def capturar_con_api(plataforma='spliiit'):
    """Capture transactions directly from each platform API."""
    import requests
    import urllib3
    from datetime import datetime, timedelta
    
    # Disable SSL warnings for corporate/proxied environments.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    session = requests.Session()
    
    if plataforma.lower() == 'spliiit':
        return capturar_spliiit_api(session)
    elif plataforma.lower() == 'together':
        return capturar_together_api(session)
    elif plataforma.lower() == 'sharingful':
        return capturar_sharingful_api(session)
    else:
        print(f"❌ Unsupported platform '{plataforma}'")
        return None

def capturar_spliiit_api(session):
    """Capture Spliiit transactions from API."""
    # SPLIIIT CONFIGURATION
    BASE_URL = "https://core.spliiit.com"
    APP_URL = "https://app.spliiit.com"
    
    # Base headers.
    session.headers.update({
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.8',
        'Origin': APP_URL,
        'Referer': f'{APP_URL}/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
    })
    
    print("\n🔑 Configuring Spliiit authentication...")
    
    print("How to get the Spliiit Bearer token:")
    print("  1. Open app.spliiit.com and log in")
    print("  2. Press F12 -> Network")
    print("  3. Reload and open the request to /api/v1/users/wallets/transactions")
    print("  4. Copy Authorization value without the 'Bearer ' prefix")

    auth_token = normalizar_token_auth(input("Enter your Bearer token (without 'Bearer '): "))
    if not auth_token:
        print("❌ Empty token")
        return None
    
    # Configure Bearer auth.
    # The same value is often present in spliiit_auth cookie as well,
    # so we also set it to mimic browser requests.
    session.headers.update({'Authorization': f'Bearer {auth_token}'})
    session.cookies.set('spliiit_auth', auth_token, domain='app.spliiit.com')
    session.cookies.set('spliiit_auth', auth_token, domain='core.spliiit.com')
    print(f"🔐 Token configured: Bearer {auth_token[:20]}...")
    
    print("📊 Fetching transactions...")
    
    # Get target month/year.
    try:
        mes = int(input("Month (1-12) [10]: ") or "10")
        año = int(input("Year [2025]: ") or "2025")
    except ValueError:
        mes, año = 10, 2025
    
    # Request transactions.
    try:
        trans_response = session.get(
            f"{BASE_URL}/api/v1/users/wallets/transactions",
            params={'month': mes, 'year': año},
            verify=False
        )
        
        print(f"🔍 Request URL: {trans_response.url}")
        print(f"📋 Status: {trans_response.status_code}")
        
        if trans_response.status_code == 200:
            print("✅ Spliiit transactions captured")
            data = trans_response.json()
            print(f"📊 Response shape: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            
            # Save raw JSON for audit
            import os
            os.makedirs('html_descargados', exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_file = f"html_descargados/spliiit_{mes:02d}_{año}_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"📝 Raw JSON saved to {json_file} for audit")
            
            return data, 'spliiit'
        else:
            print(f"❌ Error fetching transactions: {trans_response.status_code}")
            try:
                print(f"API response: {trans_response.json()}")
            except Exception:
                print(f"API response: {trans_response.text[:500]}")
            return None, 'spliiit'
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None, 'spliiit'

def capturar_together_api(session):
    """Capture Together transactions from API."""
    from datetime import datetime, timedelta
    import time
    
    # TOGETHER CONFIGURATION
    BASE_URL = "https://apiv2.togetherprice.com"
    APP_URL = "https://app.togetherprice.com"
    
    # Base headers.
    session.headers.update({
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.9,es-ES;q=0.8,es;q=0.7,fr;q=0.6',
        'Origin': APP_URL,
        'Referer': f'{APP_URL}/',
        'DNT': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'
    })
    
    print("\n🔑 Configuring Together authentication...")
    print("How to get the Together JWT token:")
    print("  1. Open app.togetherprice.com and log in")
    print("  2. Press F12 -> Network")
    print("  3. Open a request to apiv2.togetherprice.com")
    print("  4. Copy Authorization: Bearer <JWT> (do not paste the Cookie header)")
    
    auth_token = extraer_jwt_together(input("Enter Together JWT (or full Authorization header): "))
    if not auth_token:
        print("❌ Missing or invalid JWT token")
        return None
    
    # Configure Bearer auth.
    session.headers.update({'Authorization': f'Bearer {auth_token}'})
    print(f"🔐 Token configured: Bearer {auth_token[:20]}...")
    
    print("📊 Fetching Together transactions...")
    
    # Build month range in Unix milliseconds.
    try:
        mes = int(input("Month (1-12) [10]: ") or "10")
        año = int(input("Year [2025]: ") or "2025")
    except ValueError:
        mes, año = 10, 2025
    
    # Build month start/end datetimes.
    fecha_inicio = datetime(año, mes, 1)
    if mes == 12:
        fecha_fin = datetime(año + 1, 1, 1) - timedelta(days=1)
    else:
        fecha_fin = datetime(año, mes + 1, 1) - timedelta(days=1)
    
    # Convert to epoch milliseconds.
    from_timestamp = int(fecha_inicio.timestamp() * 1000)
    to_timestamp = int(fecha_fin.timestamp() * 1000)
    
    print(f"📅 Fetching range from {fecha_inicio.strftime('%d/%m/%Y')} to {fecha_fin.strftime('%d/%m/%Y')}")
    
    try:
        trans_response = session.get(
            f"{BASE_URL}/tp-financial/financial/wallet/getWalletHistory",
            params={
                'fromDate': from_timestamp,
                'toDate': to_timestamp,
                'page': 0,
                'direction': 'DESC',
                'props': 'createdAt'
            },
            verify=False
        )
        
        print(f"🔍 Request URL: {trans_response.url}")
        print(f"📋 Status: {trans_response.status_code}")
        
        if trans_response.status_code == 200:
            print("✅ Together transactions captured")
            data = trans_response.json()
            print(f"📊 Response shape: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            return data, 'together'
        else:
            print(f"❌ Error fetching transactions: {trans_response.status_code}")
            print(f"Response: {trans_response.text[:200]}...")
            if trans_response.status_code in (401, 403, 500):
                if "Authentication object was not found" in trans_response.text:
                    print("💡 Together did not receive a valid JWT. Make sure you copied Authorization: Bearer <JWT>, not Cookie.")
            return None, 'together'
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None, 'together'

def capturar_sharingful_api(session):
    """Capture Sharingful transactions from API."""
    print("\n🔑 Configuring Sharingful authentication...")
    
    auth_token = normalizar_token_auth(input("Enter your JWT token (without 'Bearer '): "))
    if not auth_token:
        print("❌ Empty token")
        return None

    # Full headers for Sharingful.
    session.headers.update({
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'en-US,en;q=0.9,es-ES;q=0.8,es;q=0.7,fr;q=0.6',
        'Authorization': f'Bearer {auth_token}',
        'Connection': 'keep-alive',
        'DNT': '1',
        'Host': 'www.sharingful.com',
        'Referer': 'https://www.sharingful.com/perfil',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        'lang': 'es',
        'locale': 'es',
        'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    })
    
    print(f"🔐 Token configured: Bearer {auth_token[:20]}...")
    jwt_ok = mostrar_jwt_info(auth_token)
    if jwt_ok is False:
        print("❌ Token has expired. Please refresh it from the browser and try again.")
        return None, 'sharingful'
    
    print("📊 Fetching Sharingful transactions...")
    
    url = "https://www.sharingful.com/api/usuario/historico-pagos"
    
    try:
        headers = {"Accept-Encoding": "gzip, deflate"}
        response = session.get(url, verify=False, headers=headers)
        
        print(f"🔍 Request URL: {response.url}")
        print(f"📋 Status: {response.status_code}")
        print(f"📬 Content-Encoding: {response.headers.get('Content-Encoding', 'none')}")
        print(f"📬 Content-Type: {response.headers.get('Content-Type', 'unknown')}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print("✅ Sharingful transactions captured")
                print(f"📊 Response shape: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                return data, 'sharingful'
            except json.JSONDecodeError as e:
                print(f"❌ Response received but is not valid JSON: {e}")
                response_sample = response.text[:300] if response.text else "[empty response]"
                print(f"First 300 chars: {response_sample}")
                print(f"Response length: {len(response.content)} bytes")
                print(f"First 50 bytes (hex): {response.content[:50].hex()}")
                print("💡 Possible causes:")
                print("   - JWT token expired (login again)")
                print("   - API endpoint changed or is down")
                print("   - User account has no data")
                print("   - Response encoding issue (GZIP not decompressed)")
                return None, 'sharingful'
        else:
            print(f"❌ Error fetching transactions: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return None, 'sharingful'
            
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return None, 'sharingful'

def cargar_desde_archivo():
    """Load transactions from an existing JSON file."""
    archivo = input("JSON file path: ")
    try:
        with open(archivo, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return None


# ============================================
# PART 2: DATA PROCESSING
# ============================================

def procesar_transacciones(datos, tipo_plataforma='spliiit', usuario_override=None):
    """Process platform transactions into a unified output schema."""
    if tipo_plataforma == 'spliiit':
        return procesar_spliiit_transacciones(datos, usuario_override)
    elif tipo_plataforma == 'together':
        return procesar_together_transacciones(datos, usuario_override)
    elif tipo_plataforma == 'sharingful':
        return procesar_sharingful_transacciones(datos, usuario_override)
    else:
        print(f"❌ Unsupported platform type '{tipo_plataforma}'")
        return []

def procesar_spliiit_transacciones(datos, usuario_override=None):
    """Process Spliiit transactions."""
    if not datos or 'data' not in datos:
        print("❌ Invalid data for Spliiit")
        return []

    # Counter by (service, year, month) so Sub resets each month
    contador_servicios_mes = defaultdict(int)
    resultados = []

    # Wallet settled statuses (general wallet view).
    estados_liquidados = {'credited', 'done', 'success', 'completed'}
    conteo_estados = defaultdict(int)
    conteo_estados_omitidos = defaultdict(int)

    for transaccion in datos['data']:
        tx = transaccion.get('transaction', {})
        estado = str(tx.get('status', '')).strip().lower()
        estado_clave = estado or '(empty)'
        conteo_estados[estado_clave] += 1

        if not (isinstance(transaccion.get('offer'), dict) and 'title' in transaccion['offer']):
            continue

        servicio = transaccion['offer']['title']
        
        amount_raw = tx.get('amount', 0)
        if not isinstance(amount_raw, (int, float)):
            continue

        # Keep only settled wallet rows.
        if estado not in estados_liquidados:
            conteo_estados_omitidos[estado_clave] += 1
            continue

        amount = float(amount_raw)
        if amount <= 0:
            continue
        tipo = 1

        # Some months return block_ending_at, others block_starting_at or created_at.
        fecha_str = (tx.get('block_ending_at') or tx.get('block_starting_at') or
                     tx.get('created_at') or tx.get('createdAt'))
        if not fecha_str:
            print(f"⚠️  Transaction without date skipped: {servicio}")
            continue

        parsed_fecha = None
        for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
            try:
                parsed_fecha = datetime.strptime(fecha_str.replace('T', ' '), fmt.replace('T', ' '))
                break
            except Exception:
                continue
        if not parsed_fecha:
            try:
                parsed_fecha = datetime.fromisoformat(fecha_str.replace('Z', '').replace('T', ' '))
            except Exception:
                parsed_fecha = None
        if not parsed_fecha:
            print(f"⚠️  Unrecognized date format: {fecha_str}, skipping transaction {servicio}")
            continue
        fecha = parsed_fecha

        # Sub index by service and month.
        clave_sub = (servicio, fecha.year, fecha.month)
        contador_servicios_mes[clave_sub] += 1

        registro = {
            'Platform': 'Spliiit',
            'Account': usuario_override or 'user1',
            'Service': servicio,
            'Sub': contador_servicios_mes[clave_sub],
            'Year': fecha.year,
            'Month': f"{fecha.month:02d}",
            'Date': fecha.date().isoformat(),
            'Revenue': amount,
            'Commission': tx.get('mkp_amount_com', ''),
            'Type': tipo,
            'Subscriber': transaccion.get('user', {}).get('name', 'Unknown')
        }

        resultados.append(registro)

    if conteo_estados_omitidos:
        detalle = ", ".join(
            f"{k}={v}" for k, v in sorted(conteo_estados_omitidos.items(), key=lambda x: x[0])
        )
        print(f"ℹ️  Spliiit non-settled statuses omitted: {detalle}")

    return resultados

def procesar_together_transacciones(datos, usuario_override=None):
    """Process Together transactions."""
    if not datos:
        print("❌ Invalid data for Together")
        return []
    
    # Counter by (service, year, month) to reset Sub each month
    contador_servicios_mes = defaultdict(int)
    resultados = []
    
    # Together may return a direct list or an object with 'body'/'content'
    if isinstance(datos, list):
        transacciones_lista = datos
    else:
        transacciones_lista = datos.get('body', [])
        if isinstance(transacciones_lista, dict):
            transacciones_lista = transacciones_lista.get('content', [])
        # Common fallback: some endpoints return data under 'data'
        if not isinstance(transacciones_lista, list) and isinstance(datos, dict):
            posible = datos.get('data', [])
            if isinstance(posible, list):
                transacciones_lista = posible
    
    if not isinstance(transacciones_lista, list):
        print("❌ Unrecognized Together structure (expected list)")
        return []
    
    for transaccion in transacciones_lista:
        # Filter PAYMENT RECEIVED transactions
        if (transaccion.get('type') == 'PAYMENT' and 
            transaccion.get('subType') == 'RECEIVED'):
            
            servicio = transaccion.get('postTitle', 'Unknown Service')
            
            # Convert timestamp to date
            timestamp = transaccion.get('creationDate', 0) / 1000
            fecha = datetime.fromtimestamp(timestamp)
            fecha_str = fecha.strftime('%Y-%m-%d')
            
            # Get amount
            amount = 0
            if 'totAmount' in transaccion and 'value' in transaccion['totAmount']:
                amount = transaccion['totAmount']['value']
            
            # Sub index by service and month
            clave_sub = (servicio, fecha.year, fecha.month)
            contador_servicios_mes[clave_sub] += 1

            registro = {
                'Platform': 'Together',
                'Account': usuario_override or 'user2',
                'Service': servicio,
                'Sub': contador_servicios_mes[clave_sub],
                'Year': fecha.year,
                'Month': f"{fecha.month:02d}",
                'Date': fecha_str,
                'Revenue': amount,
                'Commission': '',
                'Type': 1,
                'Subscriber': transaccion.get('otherFullName', 'Unknown User')
            }
            
            resultados.append(registro)
    
    return resultados

def procesar_sharingful_transacciones(datos, usuario_override=None):
    """Process Sharingful transactions."""
    if not datos:
        print("❌ Invalid data for Sharingful")
        return []
    
    # Counter by (service, year, month) to reset Sub each month
    contador_servicios_mes = defaultdict(int)
    resultados = []
    
    # Sharingful can return different structures
    print(f"📊 Inspecting Sharingful data structure...")
    print(f"Data type: {type(datos)}")
    
    if isinstance(datos, dict):
        print(f"Available keys: {list(datos.keys())}")
        # Look for the transactions list
        transacciones_lista = None
        for key in ['data', 'pagos', 'historico', 'transactions', 'payments']:
            if key in datos:
                transacciones_lista = datos[key]
                print(f"✅ Found list under key '{key}'")
                break
    elif isinstance(datos, list):
        transacciones_lista = datos
    else:
        print(f"❌ Unrecognized data structure")
        return []
    
    if not transacciones_lista:
        print("❌ No transactions found in Sharingful")
        return []
    
    print(f"📊 Processing {len(transacciones_lista)} Sharingful transactions...")
    
    for i, transaccion in enumerate(transacciones_lista):
        if isinstance(transaccion, dict):
            muestra_importe = transaccion.get('amount', transaccion.get('importe', transaccion.get('value', transaccion.get('precio', transaccion.get('price', None)))))
            print(f"📄 Transaction {i+1} raw amount: {muestra_importe}")
        
        if not isinstance(transaccion, dict):
            continue
        
        # Try to extract transaction information
        # For Sharingful, the service is in familyhistoric.categoria.nombre
        servicio = "Unknown Service"
        
        # Try familyhistoric.categoria.nombre first
        if 'familyhistoric' in transaccion and isinstance(transaccion['familyhistoric'], dict):
            familia = transaccion['familyhistoric']
            if 'categoria' in familia and isinstance(familia['categoria'], dict):
                if 'nombre' in familia['categoria']:
                    servicio = familia['categoria']['nombre']
        
        # If service is not found, try alternative fields
        if servicio == "Unknown Service":
            servicio = transaccion.get('servicio', transaccion.get('service', 
                      transaccion.get('nombre', transaccion.get('title', 'Unknown Service'))))
        
        # Date - try multiple formats
        fecha_str = transaccion.get('fecha', transaccion.get('date', 
                   transaccion.get('created_at', transaccion.get('createdAt', ''))))
        
        try:
            if isinstance(fecha_str, str):
                # Multiple date formats are possible
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                    try:
                        fecha = datetime.strptime(fecha_str.split('T')[0], fmt.split('T')[0])
                        break
                    except:
                        continue
                else:
                    fecha = datetime.now()  # Fallback
            elif isinstance(fecha_str, (int, float)):
                # Timestamp
                fecha = datetime.fromtimestamp(fecha_str if fecha_str < 10**10 else fecha_str/1000)
            else:
                fecha = datetime.now()
        except:
            fecha = datetime.now()

        # Amount - try several fields and support decimal comma
        def parse_monto(v):
            # Sharingful returns amount in cents; convert to base currency
            factor = 100.0
            if isinstance(v, (int, float)):
                return float(v) / factor
            if isinstance(v, str):
                # If there is one comma and no dot, assume decimal comma
                if v.count(',') == 1 and v.count('.') == 0:
                    v_norm = v.replace(',', '.')
                # If there are thousand separators with dot and decimal comma
                elif v.count(',') == 1 and v.count('.') >= 1:
                    v_norm = v.replace('.', '').replace(',', '.')
                else:
                    v_norm = v.replace(',', '.')
                try:
                    return float(v_norm) / factor
                except:
                    return 0.0
            return 0.0

        amount = 0.0
        for campo in ['importe', 'amount', 'cantidad', 'value', 'precio', 'price']:
            if campo in transaccion:
                valor = transaccion[campo]
                if isinstance(valor, dict) and 'value' in valor:
                    amount = parse_monto(valor.get('value'))
                else:
                    amount = parse_monto(valor)
                break
        
        # Sub index by service and month
        clave_sub = (servicio, fecha.year, fecha.month)
        contador_servicios_mes[clave_sub] += 1

        registro = {
            'Platform': 'Sharingful',
            'Account': usuario_override or 'user1',
            'Service': servicio,
            'Sub': contador_servicios_mes[clave_sub],
            'Year': fecha.year,
            'Month': f"{fecha.month:02d}",
            'Date': fecha.strftime('%Y-%m-%d'),
            'Revenue': amount,
            'Commission': '',
            'Type': 1,
            'Subscriber': transaccion.get('idUserFrom', transaccion.get('usuario', transaccion.get('user', transaccion.get('client', 'Unknown User'))))
        }
        
        resultados.append(registro)
    
    return resultados

def exportar_resultados(resultados, formato='csv'):
    """Export processed rows to CSV, Excel, or JSON."""
    if not resultados:
        print("❌ No results to export")
        return
    
    import os
    
    # Sort by date (oldest first)
    def parse_fecha(valor):
        if isinstance(valor, datetime):
            return valor
        if isinstance(valor, str) and valor:
            for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S']:
                try:
                    return datetime.strptime(valor.replace('T', ' '), fmt.replace('T', ' '))
                except Exception:
                    continue
            try:
                return datetime.fromisoformat(valor.replace('Z', '').replace('T', ' '))
            except Exception:
                return datetime.min
        return datetime.min
    resultados_ordenados = sorted(resultados, key=lambda r: parse_fecha(r.get('Date', '')))

    # Basic data for the file name (use the first sorted result)
    primero = resultados_ordenados[0]
    año = primero.get('Year', datetime.now().year)
    mes = primero.get('Month', datetime.now().strftime('%m'))
    plataforma = str(primero.get('Platform', 'platform')).lower()
    usuario = str(primero.get('Account', 'account')).replace(' ', '')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_nombre = f"{año}{mes}_{plataforma}_{usuario}_transactions_{timestamp}"

    # Normalize income with decimal comma (2 decimals) and renumber Sub by service and month (already sorted)
    from collections import defaultdict as _dd
    contador_por_servicio_mes = _dd(int)
    filas_export = []

    def _to_float(val):
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            v = val.replace('.', '').replace(',', '.') if val.count(',') == 1 and val.count('.') > 1 else val.replace(',', '.')
            try:
                return float(v)
            except:
                return 0.0
        return 0.0

    for r in resultados_ordenados:
        fila = dict(r)
        servicio = fila.get('Service', 'Service')
        # key by service and month (month may come as string "05")
        try:
            año_key = int(fila.get('Year', 0))
        except Exception:
            año_key = 0
        try:
            mes_raw = fila.get('Month', 0)
            mes_key = int(mes_raw) if mes_raw not in (None, '') else 0
        except Exception:
            mes_key = 0
        clave = (servicio, año_key, mes_key)
        contador_por_servicio_mes[clave] += 1
        fila['Sub'] = contador_por_servicio_mes[clave]

        ingreso_val = _to_float(fila.get('Revenue', 0))
        fila['Revenue'] = f"{ingreso_val:.2f}".replace('.', ',')
        filas_export.append(fila)
    
    # Ensure the out folder exists
    os.makedirs('out', exist_ok=True)
    
    if formato == 'csv':
        import csv
        archivo = f"out/{base_nombre}.csv"
        
        # utf-8-sig adds BOM so Excel correctly handles accented characters
        with open(archivo, 'w', newline='', encoding='utf-8-sig') as f:
            campos = list(filas_export[0].keys())
            writer = csv.DictWriter(f, fieldnames=campos, delimiter=';')  # Keep semicolon delimiter for spreadsheet compatibility
            writer.writeheader()
            writer.writerows(filas_export)
        
        print(f"✅ Exported to {archivo}")
    
    elif formato == 'excel':
        try:
            import pandas as pd
            archivo = f"out/{base_nombre}.xlsx"
            df = pd.DataFrame(filas_export)
            df.to_excel(archivo, index=False)
            print(f"✅ Exported to {archivo}")
        except ImportError:
            print("❌ Install pandas and openpyxl: pip install pandas openpyxl")
    
    elif formato == 'json':
        archivo = f"out/{base_nombre}.json"
        with open(archivo, 'w', encoding='utf-8') as f:
            json.dump(filas_export, f, indent=2, ensure_ascii=False)
        print(f"✅ Exported to {archivo}")
    
    return archivo


# ============================================
# PART 3: MAIN MENU
# ============================================

def main():
    """Main interactive flow."""
    parser = argparse.ArgumentParser(description='Capture and process multi-platform subscription transactions')
    parser.add_argument('--user', help='Value used in exported files for the account label')
    args = parser.parse_args()

    print("""
╔═══════════════════════════════════════════════════════════╗
║       MULTI-PLATFORM TRANSACTION AUTOMATION TOOL         ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    print("\nWhich platform do you want to capture transactions from?")
    print("1. Spliiit")
    print("2. Together")
    print("3. Sharingful")
    print("4. Load from existing JSON file")
    
    plataforma_opt = input("\nSelect platform (1-4): ").strip()
    
    plataformas = {
        '1': 'spliiit',
        '2': 'together',
        '3': 'sharingful',
        '4': 'manual'
    }
    
    plataforma = plataformas.get(plataforma_opt, 'spliiit')
    
    if plataforma != 'manual':
        metodo = 'api'
    else:
        metodo = 'manual'
        plataforma = 'manual'
    
    print("\n" + "="*60)
    
    if metodo == 'manual':
        datos = capturar_transacciones_automatico(metodo)
        tipo_plataforma = 'spliiit'
    else:
        resultado = capturar_transacciones_automatico(metodo, plataforma)
        if resultado and len(resultado) == 2:
            datos, tipo_plataforma = resultado
        else:
            datos = resultado
            tipo_plataforma = plataforma
    
    if datos:
        print("\n" + "="*60)
        print(f"🔄 Processing {tipo_plataforma.title()} transactions...")
        resultados = procesar_transacciones(datos, tipo_plataforma, args.user)
        
        if resultados:
            print(f"✅ Processed {len(resultados)} transactions")
            
            # Summary
            print("\n📊 Summary:")
            servicios = defaultdict(int)
            total = 0
            for r in resultados:
                servicios[r['Service']] += 1
                total += r['Revenue']
            
            for servicio, cantidad in servicios.items():
                print(f"  - {servicio}: {cantidad} transactions")
            print(f"  💰 Total income: {total:.2f}€")
            
            # Export
            print("\nWhich format do you want to export?")
            print("1. CSV (Excel-compatible)")
            print("2. Excel (.xlsx)")
            print("3. JSON")
            
            formato_opt = input("Format (1-3): ").strip()
            formatos = {'1': 'csv', '2': 'excel', '3': 'json'}
            formato = formatos.get(formato_opt, 'csv')
            
            print("\n" + "="*60)
            archivo = exportar_resultados(resultados, formato)
            print("\n✅ Process completed!")
        else:
            print("❌ Transactions could not be processed")
    else:
        print("\n❌ Transactions could not be captured")
        print("\n💡 Tips:")
        print("  - Verify your token and selected month/year")
        print("  - Make sure you have internet connectivity")
        print("  - Check that the application URL is correct")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Process canceled by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()