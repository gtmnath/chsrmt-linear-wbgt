# CHSRMT — Calibrated Heat-Stress Risk Management Tool

**CHSRMT** is a professional-grade occupational heat-stress management system designed for field deployment, regulatory evaluation, and research validation.  
It integrates meteorological data, physiological stress modeling, PPE and enclosure penalties, and conservative safety logic to support real-world heat-stress decisions.

Developed and maintained by **Dr. Gummanur T. Manjunath, MD**.

---

## What CHSRMT Does

CHSRMT provides **site-specific, defensible heat-stress risk classification** by combining:

- Environmental heat load (dry bulb, wet bulb, globe temperature, wind, pressure)
- Automatic weather-station integration (Open-Meteo)
- PPE, clothing, radiant heat, and vehicle/enclosure penalties
- A **Frozen WBGT baseline** architecture
- Conservative OSHA/NIOSH-aligned risk bands
- Supervisor-oriented guidance for work/rest and hydration

This allows safe and repeatable heat-stress decisions even when site conditions are being adjusted interactively.

---

## Why “Frozen WBGT” Matters

Once weather or measured environmental data are loaded, CHSRMT **freezes the baseline WBGT**.

All penalties (PPE, vehicle, radiant load, etc.) are applied **only to this frozen baseline**, not re-computed from weather each time.

This prevents:
- Hidden recalculation drift
- Circular logic errors
- Under-reporting of risk when conditions worsen

It ensures that **penalties always move risk upward**, never accidentally downward.

This architecture is required for defensible occupational-health risk management.

---

## Intended Users

CHSRMT is designed for:

- Site safety officers  
- Occupational health physicians and nurses  
- HSE managers  
- Industrial hygienists  
- Heat-stress researchers  
- Training and evaluation teams  

It is **not** a consumer weather app.

---

## Typical Use Cases

- Oil & gas rigs  
- Petrochemical plants  
- Refineries  
- Smelters  
- Mines  
- Construction sites  
- Vehicle cabins and enclosed hot spaces  
- Remote field operations  

---

## Technology Stack

- Python
- Streamlit
- Pandas
- Requests
- Open-Meteo weather API

Runs locally or in cloud environments.

---

## How to Run

```bash
pip install -r requirements.txt
streamlit run app.py
