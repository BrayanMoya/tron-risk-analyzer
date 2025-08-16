# TRON Wallet Risk Analyzer — README

Análisis de riesgo para direcciones TRON (USDT/TRC20) con **FastAPI (Python)** + **Flutter**. Genera:

* **Porcentaje de riesgo** y **nivel** (Low/Medium/High)
* **Razones explicables**
* **Exposure** (a qué está expuesta la wallet)
* **PDF** descargable con el reporte

Este README incluye instalación, uso y un **glosario para no expertos** con todos los términos que verás en el PDF.

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
    pdf_report/build.py     # Generación de PDF
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

   * Abre PowerShell o CMD:

     ```bat
     cd backend
     copy .env.example .env
     ```
   * Edita `.env` y completa:

     ```
     TRONSCAN_API_KEY=TU_KEY_OPCIONAL
     HOST=0.0.0.0
     PORT=8000
     DUST_MICRO_USDT=0.1
     DUST_SMALL_USDT=1.0
     DUST_MIN_EVENTS=3
     ```

   * Ejecuta:

     ```bat
     run.bat
     ```
   * La API queda en: `http://127.0.0.1:8000`
     Documentación interactiva: `http://127.0.0.1:8000/docs`

2. **Cliente móvil (opcional)**

   * Crea un proyecto Flutter o usa el stub de `mobile/`.
   * Construye APK apuntando al backend en tu red local:

     ```bash
     flutter build apk --release --dart-define=API_BASE=http://<TU_IP_PC>:8000
     ```
   * Instala el APK en el teléfono y prueba.

---

## 4) Endpoints

* `GET /health`
  Estado del servicio.

* `GET /risk/{address}`
  Devuelve JSON con:

  * `risk_score` (0–100)
  * `risk_level` (`Low|Medium|High`)
  * `reasons` (lista de causas y pesos)
  * `basic_info` (fechas, flujos agregados, contadores)
  * `exposure` (categorías y porcentaje)

* `GET /report/{address}`
  Genera y descarga el **PDF** del análisis.

---

## 5) ¿Cómo funciona el análisis?

### 5.1 Señales que revisa

* **Listas negras de USDT**: si la dirección está bloqueada/reportada por Tether/TronScan.
* **Flags de fraude**: si TronScan marca comportamiento sospechoso.
* **Contrapartes 1-hop**: analiza con quién transfiere la wallet (entradas/salidas). Si esas contrapartes están en riesgo, suma puntos.
* **DUST (micro-transacciones)**: muchos movimientos muy pequeños pueden indicar spam, dusting o patrones automáticos.

### 5.2 Pesos del modelo (MVP)

* `BLACKLIST_USDT` (directo): **100** (riesgo **High** inmediato)
* `FRAUD_FLAG`: **+20**
* `COUNTERPARTY_HIGH` (1-hop): **+12** por contraparte riesgosa (tope **+36**)
* `DUST_ACTIVITY`: si hay ≥ `DUST_MIN_EVENTS`
  **+5** base + **1** por evento extra (tope **+15**)

**Nivel**

* `0–29`: Low
* `30–69`: Medium
* `70–100`: High

> Los umbrales de DUST se ajustan en `.env`:
>
> * `DUST_MICRO_USDT` (p.ej. 0.10)
> * `DUST_SMALL_USDT` (p.ej. 1.00)
> * `DUST_MIN_EVENTS` (p.ej. 3)

---

## 6) Campos del PDF y cómo interpretarlos (para no expertos)

### Encabezado

* **Risk Score (0–100)**: cifra global de riesgo.
* **Risk Level**: Low / Medium / High (bajo, medio, alto).
* **Summary**: frases cortas con las señales detectadas.

### Overview

* **Inflow USDT / Outflow USDT**
  Suma aproximada de **entradas** y **salidas** de USDT (token TRC-20 en TRON) en el período analizado.

  * Se muestran con 2 decimales y separador de miles: `359,011.06`.
  * Sin notación científica (“E+…”) y con filtros para descartar outliers técnicos.
* **First tx / Last tx**
  Primera y última transferencia **observada** en el set inspeccionado, en formato `YYYY-MM-DD, h:mm am/pm` (UTC).
* **Created at / Last operation at**
  Tiempos de creación de la cuenta y última operación según TronGrid, mismos formato y zona.

### Exposure (exposición)

Mide el **porcentaje relativo** de señales dentro de lo analizado:

* **Blacklist Indirect In**: parte de la actividad que proviene de direcciones que están en listas negras/flags.
* **Blacklist Indirect Out**: parte de la actividad que va hacia esas direcciones.
* **Dust In (USDT) / Dust Out (USDT)**: cuánta presencia tienen las micro-transacciones en entradas/salidas.
  Útil para detectar spam/dusting u operaciones automatizadas.
* **DEX / Exchange** (si se habilitan listas): interacción con contratos de exchanges o casas de cambio. Informativo.

> **Importante**: “Exposure” no es dinero perdido ni congelado; es un **mapa de riesgo** de con quién/qué interactúa la wallet.

### Reasons (razones)

Tabla con **códigos** y **pesos** que componen el score:

* `BLACKLIST_USDT`
  La dirección aparece en listas negras de USDT. Sube el score a 100.
* `BLACKLIST_USDT_EVIDENCE`
  Evidencia adicional de blacklist establecoin (misma severidad).
* `FRAUD_FLAG`
  TronScan marcó señales de fraude/abuso. Suma +20.
* `COUNTERPARTY_HIGH`
  Se detectaron `n` contrapartes a 1 salto con alto riesgo. Suma +12 por cada una (hasta +36).
* `DUST_ACTIVITY`
  Se detectaron muchos movimientos muy pequeños (contados como “dust”). Suma +5 (mínimo) más +1 por evento extra (hasta +15).

### Otros términos frecuentes

* **TRON / TRX / TRC-20**

  * **TRON**: la red blockchain.
  * **TRX**: moneda nativa de TRON (parecida a “ETH” en Ethereum).
  * **TRC-20**: estándar de token en TRON (ej.: USDT en TRON es un TRC-20).
* **USDT (Tether)**
  Stablecoin cuyo valor suele mantenerse cerca de 1 USD. En TRON, el contrato oficial es único; los cálculos solo usan ese contrato para evitar confusiones.
* **Address (dirección)**
  Identificador de la wallet. En TRON comienza con **T…**.
* **1-hop (un salto)**
  Contrapartes que interactuaron **directamente** con la wallet (entradas o salidas).
  *Ejemplo:* A ↔ **B** (tú) ↔ C → **A** y **C** son **1-hop** respecto de **B**.
* **Blacklist (lista negra)**
  Listado de direcciones bloqueadas o reportadas por incumplimientos, sanciones, fraudes, etc.
* **Dust (polvo)**
  Transacciones **muy pequeñas**. Por sí solas no implican delito, pero en conjunto pueden indicar *spamming* o intentos de rastreo.

---

## 7) Buenas prácticas y límites

* El score es **heurístico**, no un dictamen legal. Úsalo como **señal** para priorizar revisiones.
* **Privacidad**: el sistema consulta APIs públicas.
* **Cobertura**: el análisis se centra en **USDT (TRC-20)** y señales más comunes. Puedes ampliar a otros tokens o categorías (DEX/CEXs etiquetados) añadiendo listas.
* **Recencia de datos**: algunas APIs tienen paginación o límites. Si necesitas un histórico más amplio, implementa paginado/lotes.

---

## 8) Personalización rápida

* **Ajustar sensibilidad DUST**: edita `.env`

  ```
  DUST_MICRO_USDT=0.1
  DUST_SMALL_USDT=1.0
  DUST_MIN_EVENTS=3
  ```

  Más bajo → más sensible (más eventos contarán como dust).
* **Recalibrar pesos**: `backend/app/risk_engine/weights.py`

  * `COUNTERPARTY_HIT`, `COUNTERPARTY_CAP`
  * `DUST_BASE`, `DUST_PER_EVENT`, `DUST_CAP`
* **Agregar tokens**: replica la lógica de USDT para otros contratos (filtrando por “address” del contrato correspondiente).

---

## 9) Solución de problemas

* **401 Unauthorized (TronScan)**
  Asegúrate de que `TRONSCAN_API_KEY` esté en `.env` y que el backend **cargue** ese `.env`. El proyecto ya usa `python-dotenv`.
* **No carga el .env**
  Ejecuta desde la carpeta `backend/` y verifica que `.env` esté allí. Reinicia `run.bat`.
* **No aparece el PDF**
  Abre el endpoint `GET /report/{address}` desde el navegador o desde la app (asegúrate de que la IP del backend sea accesible desde el teléfono).
* **Notación científica o muchos decimales**
  Ya se formatean cantidades a 2 decimales con separador de miles, y se filtran outliers. Si ves algo raro, revisa la fuente (transacciones de otro token o datos corruptos).

---

## 10) Roadmap sugerido

* Paginado para cubrir más de 200 transferencias TRC-20.
* Etiquetado de **DEX/Exchanges** y categorías adicionales (juegos, mixers, gambling).
* Conversión a **USD histórico** por fecha (si quieres ver valores en fiat).
* “Motivos ampliados” por transacción (trail de evidencias) en el PDF largo.

---

## 11) Descargo de responsabilidad

Este software proporciona **indicadores de riesgo** con fines informativos. No constituye asesoría financiera ni de cumplimiento. Verifica siempre con tus propios criterios/controles adicionales.

---

## 12) Ejemplo de interpretación rápida

> **Risk Score 62 (Medium)**
>
> * Razones: `DUST_ACTIVITY` (+12), `COUNTERPARTY_HIGH` (+24), `FRAUD_FLAG` (+20)
> * Exposure: **Dust In 40%**, **Blacklist Indirect Out 35%**, **Dust Out 25%**
> * Acción: vigilar nuevas transacciones; evitar interacción hasta clarificar contrapartes; considerar monitoreo más frecuente.