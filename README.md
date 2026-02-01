# TRON Wallet Risk Analyzer — README

Análisis de riesgo para direcciones TRON (USDT/TRC20) con **FastAPI (Python)**.
Genera:

* **Porcentaje de riesgo** y **nivel** (Low/Medium/High)
* **Razones explicables** (códigos y pesos)
* **Exposure** (a qué está expuesta la wallet)
* **PDF** descargable con el reporte completo:

  * **Direcciones y transacciones clicables** (abren en TronScan)
  * **Evidencia de blacklist (USDT)**
  * **Tabla de transacciones relevantes** alrededor del bloqueo

---

## 1) Requisitos

* **Windows 10/11**
* **Python 3.10+**
* (Opcional) **Flutter 3+** para la app móvil
* Conexión a Internet (consulta APIs públicas de TRON)

---

## 2) Estructura del proyecto

```
backend/
  app/
    main.py                 # FastAPI
    pdf_report/build.py     # Generación de PDF (enlaces y tablas)
    risk_engine/
      core.py               # Lógica de scoring
      weights.py            # Pesos del modelo
    sources/
      tronscan.py           # Conectores TRONSCAN
      trongrid.py           # Conectores TronGrid
    storage/
      db.py, models.py      # SQLite (opcional)
    utils/
      address.py            # Utilidades de direcciones TRON
  .env.example
  requirements.txt
  run.bat
mobile/ (opcional, Flutter)
  lib/
  pubspec.yaml
```

---

## 3) Instalación y arranque (Windows)

1. **Backend**

```bat
cd backend
copy .env.example .env
```

Edita `.env` y completa (ver tabla de variables abajo). Luego:

```bat
run.bat
```

* API: `http://127.0.0.1:8000`
* Docs: `http://127.0.0.1:8000/docs`

---

## 4) Variables de entorno

| Variable            | Descripción                                                                       | Ejemplo / Default                    |
| ------------------- | --------------------------------------------------------------------------------- | ------------------------------------ |
| `HOST`              | Host del servidor FastAPI.                                                        | `0.0.0.0`                            |
| `PORT`              | Puerto del servidor.                                                              | `8000`                               |
| `TRONGRID_API_KEY`  | API key de TronGrid (recomendable para evitar rate limits).                       | *(vacío)*                            |
| `TRONSCAN_API_KEY`  | API key de TronScan (opcional, pero recomendable).                                | *(vacío)*                            |
| `USDT_CONTRACT`     | Contrato oficial de USDT TRC-20 que se analiza.                                   | `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` |
| `USDT_MAX_EVENT`    | Máximo valor permitido por evento (sanidad de datos).                             | `1e12`                               |
| `DUST_MICRO_USDT`   | Umbral para “micro” (USDT).                                                       | `0.1`                                |
| `DUST_SMALL_USDT`   | Umbral para “small” (USDT).                                                       | `1.0`                                |
| `DUST_MIN_EVENTS`   | Mínimo de eventos “dust” para activar penalización.                               | `3`                                  |
| `BL_TIME_WINDOW_MS` | Ventana temporal ± alrededor del evento de blacklist para la tabla de relevancia. | `259200000` (3 días)                 |
| `BL_MIN_USDT`       | Mínimo de USDT por transferencia para aparecer en la tabla de relevancia.         | `10000`                              |
| `RISK_SUSPECTS`     | Lista (coma-separada) de addresses a marcar como “sospechosas” explícitas.        | `TQQeZmH1ZU2AFv3c93rZaKUZ2bftTGxDK9` |

> **Notas**
> • El sistema sólo computa **USDT TRC-20** del contrato oficial.
> • `RISK_SUSPECTS` complementa la detección de contrapartes riesgosas 1-hop.

---

## 5) Endpoints

| Método | Endpoint            | Descripción                                                    |
| ------ | ------------------- | -------------------------------------------------------------- |
| `GET`  | `/health`           | Estado del servicio.                                           |
| `GET`  | `/risk/{address}`   | JSON con score, nivel, razones, exposure, básicos y evidencia. |
| `GET`  | `/report/{address}` | Genera y descarga el **PDF** completo.                         |

### JSON con análisis
  * `risk_score` (0–100)
  * `risk_level` (`Low|Medium|High`)
  * `reasons` (lista de causas y pesos)
  * `basic_info` (fechas, flujos agregados, contadores)
  * `exposure` (categorías y porcentaje)
---

## 6) ¿Cómo funciona el análisis?

### 6.1 Señales que revisa

* **Listas negras de USDT** (contrato oficial): si la dirección está en blacklist del token.
* **Flags de fraude** (TronScan): marcadores de actividad sospechosa.
* **Contrapartes 1-hop**: con quién interactúa directamente (entradas/salidas). Si esas contrapartes tienen riesgo, suma puntos.
* **DUST** (micro-transacciones): actividad con montos muy pequeños (spam/dusting/patrones automáticos).
* **Evidencia de blacklist**: si existe, captura **hash, timestamp, ejecutor multisig** y **transacciones relevantes** alrededor del evento.

### 6.2 Pesos del modelo (MVP)

* `BLACKLIST_USDT` (directo): **100** (riesgo **High** inmediato)
* `BLACKLIST_USDT_EVIDENCE`: se eleva a severidad de blacklist si no vino por `is_black_list`.
* `FRAUD_FLAG`: **+20**
* `COUNTERPARTY_HIGH` (1-hop): **+12** por contraparte (tope **+36**)
* `DUST_ACTIVITY`: si hay ≥ `DUST_MIN_EVENTS` → **+5** base + **1** por evento extra (tope **+15**)

**Niveles:** `0–29` Low, `30–69` Medium, `70–100` High

> Los umbrales DUST se ajustan en `.env`:
> `DUST_MICRO_USDT`, `DUST_SMALL_USDT`, `DUST_MIN_EVENTS`.

---

## 7) Qué contiene el PDF

> El PDF está pensado para que **cualquiera** (no técnico) pueda leerlo y **verificar** en TronScan con un clic.

### 7.1 Encabezado general

| Campo                  | Qué es                                            | Cómo leerlo                                 |
| ---------------------- | ------------------------------------------------- | ------------------------------------------- |
| **Address**            | La dirección TRON analizada (empieza por **T…**). | Identifica la wallet dueña de los fondos.   |
| **Risk Score (0–100)** | Puntaje global del modelo.                        | Cuanto más alto, más señales de riesgo.     |
| **Risk Level**         | Low / Medium / High.                              | Traducción del puntaje a nivel.             |
| **Resumen**            | Frase corta con las señales más fuertes.          | Contexto rápido para ejecutivos/compliance. |

### 7.2 Overview (básicos operativos)

| Campo                           | Qué es                                                     | Cómo leerlo                                   |
| ------------------------------- | ---------------------------------------------------------- | --------------------------------------------- |
| **Entradas (TRC20 USDT aprox)** | Suma de USDT recibidos (filtrando outliers).               | 2 decimales + miles (p. ej., `359,011.06`).   |
| **Salidas (TRC20 USDT aprox)**  | Suma de USDT enviados.                                     | Igual formato que entradas.                   |
| **Primera transferencia**       | Marca de tiempo (UTC) de la primera transacción observada. | `YYYY-MM-DD, h:mm am/pm`.                     |
| **Última transferencia**        | Marca de tiempo (UTC) de la última transacción observada.  | Ayuda a ver actividad reciente.               |
| **Dust In / Dust Out / Total**  | Número de micro/small tx (según umbrales).                 | Mucho “dust” puede ser spam o automatización. |

### 7.3 Evidencia de Blacklist (USDT)

> Esta sección **aparece sólo** si la wallet está listada en el **contrato oficial** de USDT.

| Campo                | Qué es                                                                | Cómo leerlo                                               |
| -------------------- | --------------------------------------------------------------------- | --------------------------------------------------------- |
| **Tx hash**          | Transacción que ejecutó el `AddedBlackList(address)`.                 | **Clic** en `[Ver en TronScan]` abre el detalle on-chain. |
| **Fecha/Hora (UTC)** | Momento exacto en que se aplicó el bloqueo.                           | Sirve para correlacionar con movimientos previos.         |
| **Ejecutor**         | Contrato **MultiSigWallet** del emisor (Tether) que aprobó la acción. | Confirma que el freeze vino del admin del token.          |
| **Nota**             | Descripción técnica breve.                                            | Por qué no podrás transferir USDT desde esa address.      |

#### 7.3.1 Tabla: Transacciones relevantes alrededor del bloqueo

Se listan **entradas/salidas USDT** en una **ventana temporal** configurable (`BL_TIME_WINDOW_MS`) y **montos ≥ `BL_MIN_USDT`**.

| Columna               | Qué es                                                               | Cómo leerlo                                                                               |
| --------------------- | -------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **Fecha (UTC)**       | Momento de la transferencia.                                         | Línea de tiempo para ver contexto.                                                        |
| **Dir**               | `IN` o `OUT`.                                                        | Si recibiste o enviaste USDT.                                                             |
| **From**              | Dirección origen. **Clic** para abrir en TronScan.                   | Puedes validar quién te pagó.                                                             |
| **To**                | Dirección destino. **Clic** para abrir en TronScan.                  | Puedes validar a quién pagaste.                                                           |
| **USDT**              | Monto transferido. **Clic** para abrir la transacción (si hay hash). | Verifica el evento exacto en TronScan.                                                    |
| **🔴 (marca visual)** | “Sospechosa / causa probable”.                                       | Se activa si: aparece en `RISK_SUSPECTS` o fue detectada como contraparte riesgosa 1-hop. |

> **Idea clave:** la tabla ayuda a **evidenciar** qué transacciones (p. ej. desde una address con riesgo medio) **pudieron motivar** el blacklist.

### 7.4 Exposure (mapa de exposición)

| Categoría                             | Qué mide                                                 | Ejemplo de lectura                             |
| ------------------------------------- | -------------------------------------------------------- | ---------------------------------------------- |
| **Blacklist Indirect In / Out**       | Porción relativa de actividad con contrapartes marcadas. | Si es alto, hay contacto frecuente con riesgo. |
| **Dust In / Dust Out**                | Peso de micro-transacciones.                             | Mucho dust puede ser spam/dusting o bots.      |
| **DEX / Exchange** *(si se habilita)* | Interacción con DEX/CEX etiquetados.                     | Útil para ver hábitos de la wallet.            |

> **No es dinero congelado ni perdido**; es un **mapa** de con quién y cómo interactúa la wallet.

### 7.5 Reasons (razones del score)

| Código                    | Significado                                        | Efecto en score                                  |
| ------------------------- | -------------------------------------------------- | ------------------------------------------------ |
| `BLACKLIST_USDT`          | Aparece en blacklist del contrato USDT.            | Fuerza **High** (≈100).                          |
| `BLACKLIST_USDT_EVIDENCE` | Confirmación por endpoint de stablecoin blacklist. | Misma severidad si aplica.                       |
| `FRAUD_FLAG`              | TronScan detecta patrones de fraude/abuso.         | **+20**                                          |
| `COUNTERPARTY_HIGH`       | `n` contrapartes 1-hop con riesgo.                 | **+12** c/u (tope **+36**).                      |
| `DUST_ACTIVITY`           | Actividad micro/small elevada.                     | **+5** base + **1**/evento extra (tope **+15**). |

---

## 8) Glosario
| Término                     | Explicación llana                                                                                    |
| --------------------------- | ---------------------------------------------------------------------------------------------------- |
| **TRON**                    | La red blockchain.                                                                                   |
| **TRX**                     | Moneda nativa de TRON (como “ETH” en Ethereum).                                                      |
| **TRC-20**                  | Estándar de token en TRON (USDT en TRON es TRC-20).                                                  |
| **USDT (Tether)**           | Stablecoin ≈ 1 USD. Tiene funciones de **blacklist** a nivel de contrato.                            |
| **Address**                 | Identificador de una wallet (empieza por **T**).                                                     |
| **1-hop**                   | Contrapartes que interactúan **directamente** con tu wallet.                                         |
| **Smart Contract Account**  | Cuenta controlada por **código**, no por clave privada (ej.: multisig).                              |
| **MultiSigWallet**          | Contrato que requiere múltiples firmas para ejecutar una acción (ej.: listar en blacklist).          |
| **AddedBlackList(address)** | Evento del contrato USDT que bloquea a esa dirección para enviar USDT.                               |
| **Dust**                    | Transacciones muy pequeñas; por sí solas no son delito, pero en conjunto pueden indicar spam o bots. |
| **TronScan**                | Explorador para ver transacciones, balances, eventos y listas negras.                                |

---

## 9) Buenas prácticas y límites

* El score es **heurístico**; no es un dictamen legal.
* Privacidad: se consultan **APIs públicas** (TronGrid/TronScan).
* Foco en **USDT TRC-20**; ampliar a otros tokens es sencillo replicando la lógica.
* Recencia: usa paginación si necesitas histórico más amplio que 200 TRC-20.

---

## 10) Personalización rápida

* **Sensibilidad DUST** (`.env`):

```ini
DUST_MICRO_USDT=0.1
DUST_SMALL_USDT=1.0
DUST_MIN_EVENTS=3
```

* **Ventana de evidencia** (tabla alrededor de blacklist):

```ini
BL_TIME_WINDOW_MS=259200000   # 3 días
BL_MIN_USDT=10000             # umbral de monto
```

* **Sospechosos explícitos**:

```ini
RISK_SUSPECTS=TQQeZmH1ZU2AFv3c93rZaKUZ2bftTGxDK9,OTRA_ADDRESS
```

* **Pesos**: `backend/app/risk_engine/weights.py`
  `COUNTERPARTY_HIT`, `COUNTERPARTY_CAP`, `DUST_BASE`, `DUST_PER_EVENT`, `DUST_CAP`, etc.

---

## 11) Solución de problemas

* **401 Unauthorized (TronScan)** → agrega `TRONSCAN_API_KEY` al `.env` y reinicia.
* **.env no carga** → ejecuta desde `backend/` (ya usamos `python-dotenv`).
* **PDF no descarga** → prueba `GET /report/{address}` en navegador; verifica IP/puerto accesibles.
* **Cantidades raras o en notación científica** → ya formateamos 2 decimales + miles y filtramos outliers; valida que sean **USDT TRC-20** del contrato oficial.

---

## 12) Roadmap sugerido

* Paginado para cubrir >200 transferencias TRC-20.
* Etiquetado DEX/CEX adicional y nuevas categorías (mixers, gambling, juegos).
* Conversión a USD histórico por fecha.
* PDF extendido con **trail de evidencias por transacción**.

---

## 13) Descargo de responsabilidad

Este software proporciona **indicadores de riesgo** con fines informativos.
No constituye asesoría financiera/compliance. Usa controles adicionales propios.

---

## 14) Ejemplo de interpretación rápida

> **Risk Score 62 (Medium)**
>
> * Razones: `DUST_ACTIVITY` (+12), `COUNTERPARTY_HIGH` (+24), `FRAUD_FLAG` (+20)
> * Exposure: **Dust In 40%**, **Blacklist Indirect Out 35%**, **Dust Out 25%**
> * Acción: vigilar nuevas transacciones; evitar interacción hasta clarificar contrapartes; considerar monitoreo continuo.
