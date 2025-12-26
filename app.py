# ======================================================================
# BLOCK 1 — Imports, page config, utilities, session defaults
# ======================================================================
"""
CHSRMT — Proprietary Evaluation License

Copyright (c) 2025
Dr. Gummanur T. Manjunath, MD
All Rights Reserved

This software package, known as CHSRMT (Calibrated Heat-Stress Risk Management Tool),
including its source code, algorithms, models, penalty systems, frozen WBGT baseline,
risk classification logic, user interface, and all derivative works, is the exclusive
intellectual property of Dr. Gummanur T. Manjunath.

Permission is granted to view, install, and run this software for:
- Professional evaluation
- Occupational health field trials
- Training and demonstration
- Academic or research validation

The following are strictly prohibited without written permission:
- Redistribution of this software or any portion of it
- Publishing as part of another tool, website, or product
- Commercial use, resale, or licensing
- Use in regulatory, compliance, or safety-critical decision making
- Modification or creation of derivative works

This software is provided “as is” without warranty of any kind.
The author is not responsible for decisions or outcomes based on its use.

For permissions contact:
Dr. Gummanur T. Manjunath
"""


import math
import pandas as pd
import requests
import streamlit as st
from datetime import datetime

APP_VERSION = "v1.9.25_linearWBGT"

st.set_page_config(
    page_title=f"CHSRMT {APP_VERSION}",
    layout="wide",
)

st.markdown("""
<style>

/* Compact mobile-friendly typography */
h1 {font-size: 1.45rem !important; margin-bottom: 0.3rem;}
h2 {font-size: 1.25rem !important; margin-bottom: 0.25rem;}
h3 {font-size: 1.05rem !important; margin-bottom: 0.2rem;}
div[data-testid="stMarkdownContainer"] p {margin-bottom: 0.25rem;}

/* Welcome gate styling */
.welcome-box {
    background: linear-gradient(90deg, #0f4c75, #3282b8);
    padding: 1rem;
    border-radius: 10px;
    color: white;
    margin-bottom: 0.8rem;
}
.welcome-box h2 {
    font-size: 1.35rem;
    margin-bottom: 0.2rem;
}
.welcome-box p {
    font-size: 0.9rem;
    opacity: 0.9;
}

/* Section titles after landing */
.section-title {
    color: #1f6fb2;
    font-weight: 600;
    font-size: 1.1rem;
    margin-top: 0.7rem;
    margin-bottom: 0.15rem;
}
.section-sub {
    color: #5f7f9c;
    font-size: 0.88rem;
    margin-bottom: 0.3rem;
}

</style>
""", unsafe_allow_html=True)

# st.markdown("""
# <style>
# h1 {font-size: 1.6rem !important;}
# h2 {font-size: 1.35rem !important; margin-bottom: 0.3rem;}
# h3 {font-size: 1.15rem !important; margin-bottom: 0.25rem;}
# div[data-testid="stMarkdownContainer"] p {margin-bottom: 0.35rem;}
# </style>
# """, unsafe_allow_html=True)

# ============================================================== 
# BLOCK 0-A — LANDING / WELCOME GATE (PROPERLY GATED)
# ==============================================================

ss = st.session_state
if "landing_open" not in ss:
    ss["landing_open"] = False

if not ss["landing_open"]:
    st.markdown("""
    <div class="welcome-box">
        <h2>☀️ CHSRMT — Heat-Stress Risk Predictor</h2>
        <p>Field-ready WBGT assessment with penalties, OSHA/NIOSH thresholds,
        hydration and acclimatization guidance.</p>
        <p><b>Workflow:</b> Weather → Baseline → Penalties → Classification → Action → Logging</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### What this tool does")
    st.markdown("""
    • Calculates WBGT  
    • Applies PPE, enclosure and radiant penalties  
    • Classifies heat stress  
    • Gives supervisor guidance  
    """)

    st.warning("This tool supports professional judgment and does not replace site HSE or medical protocols.")

    if st.button("🚀 Start Heat-Stress Assessment"):
        ss["landing_open"] = True
        st.rerun()

    st.stop()
 
# ======================================================================
# WORKING PAGE HEADER (shown after landing gate opens)
# ======================================================================

st.markdown("<div class='section-title'>🌡️ CHSRMT — Field Heat-Stress Dashboard</div>", unsafe_allow_html=True)
st.markdown("<div class='section-sub'>Location → Weather → Baseline → Penalties → Classification → Action → Logging</div>", unsafe_allow_html=True)

st.markdown("""
Enter local measurements if available.  
Or search a city and fetch weather for an approximate site baseline.  
Scroll down for thresholds, guidance and appendix.
""")

# st.title("🌡️ CHSRMT — Field Heat-Stress Dashboard")

# ----------------------------
# Unit conversion helpers
# ----------------------------
def c_to_f(c): return (c * 9/5) + 32
def f_to_c(f): return (f - 32) * 5/9
def ms_to_mph(v): return v * 2.23694
def mph_to_ms(v): return v / 2.23694
def kpa_to_inhg(k): return k * 0.2953
def inhg_to_kpa(i): return i / 0.2953

# ----------------------------
# Temperature formatting
# ----------------------------
def fmt_temp(temp_c, unit):
    return f"{temp_c:.1f} °C" if unit=="metric" else f"{c_to_f(temp_c):.1f} °F"

# ----------------------------
# Safe session init
# ----------------------------
ss = st.session_state
def ss_default(key, val):
    if key not in ss:
        ss[key] = val

# Core environmental storage (always internally °C, m/s, kPa)
ss_default("units", "metric")        # User display choice — metric or imperial
ss_default("db_c", 32.0)            # Dry bulb °C
ss_default("rh_pct", 60.0)          # Relative humidity %
ss_default("ws_ms", 1.0)            # Wind speed m/s
ss_default("p_kpa", 101.3)          # Pressure kPa
ss_default("gt_c", 35.0)            # Globe temperature °C

# WBGT storage
ss_default("wbgt_raw_c", None)
ss_default("wbgt_eff_c", None)

# Risk thresholds (NIOSH-aligned defaults)
ss_default("thr_green_c", 29.0)   # Below 29 = Low
ss_default("thr_amber_c", 32.0)   # 29–32 caution
ss_default("thr_red_c", 32.0)     # above 32 = withdrawal

# Penalty storage
ss_default("pen_clo_c", 0.0)
ss_default("pen_veh_c", 0.0)
ss_default("pen_rad_c", 0.0)
ss_default("pen_adhoc_c", 0.0)
ss_default("total_penalty_c", 0.0)

# Logging array
ss_default("audit_log", [])

# ======================================================================
# BLOCK 2 — Sidebar controls (Units & risk band display)
# ======================================================================

with st.sidebar:
    st.title("Heat-Stress Controls")

    # -------------------------
    # Environmental Input Units
    # -------------------------
    unit_choice = st.radio(
        "Display Units For Environmental Inputs",
        ["metric (°C, m/s, kPa)", "imperial (°F, mph, inHg)"],
        index=0 if ss.get("units", "metric") == "metric" else 1,
    )
    ss["units"] = "metric" if unit_choice.startswith("metric") else "imperial"

    st.markdown("---")

    # ------------------------------
    # WBGT - Risk Band Display Units
    # ------------------------------
    band_choice = st.radio(
        "Risk Band Display Units",
        ["metric (°C)", "imperial (°F)"],
        index=0 if ss.get("band_units", "metric") == "metric" else 1,
    )
    ss["band_units"] = "metric" if band_choice.startswith("metric") else "imperial"

    # ---- Show risk band numbers (THIS WAS MISSING) ----
    A = ss.get("thr_A_c", 29.0)
    B = ss.get("thr_B_c", 32.0)
    C = ss.get("thr_C_c", 35.0)

    st.markdown("**Risk band reference:**")
    st.write(f"🟢 Low Risk Zone: < {fmt_temp(A, ss['band_units'])}")
    st.write(f"🟠 Caution Zone: {fmt_temp(A, ss['band_units'])} – {fmt_temp(B, ss['band_units'])}")
    st.write(f"🔴 Withdrawal Zone: ≥ {fmt_temp(C, ss['band_units'])}")

    st.markdown("---")
    st.caption(f"App build: {APP_VERSION}")

# ======================================================================
# BLOCK 3 — LOCATION SEARCH (OPEN-METEO GEOCODER)
# ======================================================================

st.markdown("## 🛰 Location Search (City Lookup)")

place_query = st.text_input(
    "Enter a city name",
    value="",
    placeholder="Example: Dubai, Dallas, Chennai, Phoenix",
)

search_btn = st.button("🔍 Search city")

if search_btn and place_query.strip():
    url = (
        "https://geocoding-api.open-meteo.com/v1/search?"
        f"name={place_query}&count=10&language=en&format=json"
    )
    resp = requests.get(url).json()

    results = resp.get("results", [])

    if not results:
        st.error("❌ No matching locations found — refine your spelling.")
    else:
        # Build a list of readable labels
        labels = []
        for r in results:
            name = r.get("name", "")
            admin = r.get("admin1", "")
            cc = r.get("country_code", "")
            labels.append(f"{name}, {admin}, {cc}")

        choice = st.selectbox(
            "Select the exact location",
            options=labels,
            key="place_pick",
        )

        if choice:
            idx = labels.index(choice)
            loc = results[idx]
            ss["lat"] = loc.get("latitude", None)
            ss["lon"] = loc.get("longitude", None)
            ss["place_label"] = choice

            st.success(
                f"📍 Selected: **{choice}** "
                f"(lat {ss['lat']:.3f}, lon {ss['lon']:.3f})"
            )
else:
    st.info("Enter a name and press **Search city** to begin.")
# ======================================================================
# BLOCK 4 — FETCH WEATHER & POPULATE ENVIRONMENTAL INPUTS
# ======================================================================

st.markdown("## 🌡 Env. Input Fields (Auto or Manual Entry)")

# Button to manually trigger weather pull
fetch_btn = st.button("🌤 Fetch Weather Now (Open-Meteo)")

if fetch_btn:
    lat = ss.get("lat", None)
    lon = ss.get("lon", None)

    if lat is None or lon is None:
        st.error("❗ Set a valid location first (use Search City).")
    else:
        url = (
            "https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            "&current=temperature_2m,relative_humidity_2m,"
            "wind_speed_10m"
            "&pressure_unit=hpa"
        )
        data = requests.get(url).json()
        current = data.get("current", {})

        # Extract values from API
        temp_c = float(current.get("temperature_2m", ss["db_c"]))
        rh_pct = float(current.get("relative_humidity_2m", ss["rh_pct"]))
        ws_ms = float(current.get("wind_speed_10m", ss["ws_ms"]))
        # Pressure comes only in daily blocks, so default 101.3 kPa
        p_kpa = 101.3

        # STORE INTERNAL (°C, m/s, kPa)
        ss["db_c"] = temp_c
        ss["rh_pct"] = rh_pct
        ss["ws_ms"] = ws_ms
        ss["p_kpa"] = p_kpa

        # AUTO-ESTIMATED GT = DB + 3°C
        ss["gt_c"] = temp_c + 3.0

        st.success(
            f"Weather updated from Open-Meteo at {datetime.utcnow().strftime('%H:%M UTC')}."
        )

# ------------------------------------------------------------------
# MANUAL ENTRY INPUTS (with unit conversions)
# ------------------------------------------------------------------

col1, col2, col3, col4, col5 = st.columns(5)

# DB
with col1:
    if ss["units"] == "metric":
        db_in = st.number_input("Dry Bulb (°C)", value=float(ss["db_c"]))
        ss["db_c"] = db_in
    else:
        db_f = st.number_input("Dry Bulb (°F)", value=float(c_to_f(ss["db_c"])))
        ss["db_c"] = f_to_c(db_f)

# RH
with col2:
    rh_in = st.number_input("RH (%)", value=float(ss["rh_pct"]), min_value=0.0, max_value=100.0)
    ss["rh_pct"] = rh_in

# Wind
with col3:
    if ss["units"] == "metric":
        ws_val = st.number_input("Wind (m/s)", value=float(ss["ws_ms"]))
        ss["ws_ms"] = ws_val
    else:
        ws_mph = st.number_input("Wind (mph)", value=float(ms_to_mph(ss["ws_ms"])))
        ss["ws_ms"] = mph_to_ms(ws_mph)

# Pressure
with col4:
    if ss["units"] == "metric":
        p_val = st.number_input("Pressure (kPa)", value=float(ss["p_kpa"]))
        ss["p_kpa"] = p_val
    else:
        p_inhg = st.number_input("Pressure (inHg)", value=float(kpa_to_inhg(ss["p_kpa"])))
        ss["p_kpa"] = inhg_to_kpa(p_inhg)

# GT estimated field (user can override later)
with col5:
    if ss["units"] == "metric":
        gt_in = st.number_input("Globe Temp est (°C)", value=float(ss["gt_c"]))
        ss["gt_c"] = gt_in
    else:
        gt_f = st.number_input("Globe Temp est (°F)", value=float(c_to_f(ss["gt_c"])))
        ss["gt_c"] = f_to_c(gt_f)
# ======================================================================
# BLOCK 5 — COMPUTE NATURAL WET-BULB + WBGT BASELINE (with frozen baseline)
# ======================================================================

st.markdown("## 🧮 Baseline WBGT Calculation (Before Penalties)")

# Pull current internal values (always in °C internally)
db_c  = float(ss["db_c"])
rh    = float(ss["rh_pct"])
ws_ms = float(ss["ws_ms"])
gt_c  = float(ss["gt_c"])
p_kpa = float(ss["p_kpa"])

# ---------------------------------------------------------------
# RESET frozen baseline when core environmental inputs change
# (and clear any previously applied penalties)
# ---------------------------------------------------------------
if "prev_env" not in ss:
    ss["prev_env"] = {}

env_now = {"db": db_c, "rh": rh, "gt": gt_c, "ws": ws_ms}
if ss["prev_env"] != env_now:
    ss["wbgt_base_frozen"] = None
    ss["penalties_applied"] = False
    ss["total_penalty_c"] = 0.0
    # Reset effective to baseline (will be set after baseline is computed)
    ss["wbgt_eff_c"] = None

ss["prev_env"] = env_now

# ---------------------------------------------------------------
# Natural Wet-Bulb (Stull)
# ---------------------------------------------------------------
twb_c = (
    db_c * math.atan(0.151977 * math.sqrt(rh + 8.313659))
    + math.atan(db_c + rh)
    - math.atan(rh - 1.676331)
    + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
    - 4.686035
)
ss["twb_c"] = twb_c

# ---------------------------------------------------------------
# Wind-corrected Globe Temperature (ISO-7243 style damping)
# (If you don’t want wind correction, set gt_adj = gt_c)
# ---------------------------------------------------------------
v = max(ws_ms, 0.1)  # avoid divide-by-zero
f_v = 1.0 / (1.0 + 0.4 * math.sqrt(v))
gt_adj = db_c + (gt_c - db_c) * f_v

# ---------------------------------------------------------------
# WBGT outdoor ISO (use gt_adj here)
# ---------------------------------------------------------------
wbgt_raw_c = 0.7 * twb_c + 0.2 * gt_adj + 0.1 * db_c
ss["wbgt_raw_c"] = wbgt_raw_c
ss["wbgt_base_c"] = wbgt_raw_c

# Freeze baseline once per stable environment
if ss.get("wbgt_base_frozen") is None:
    ss["wbgt_base_frozen"] = wbgt_raw_c

# If penalties are NOT applied, keep effective tied to frozen baseline
if not ss.get("penalties_applied", False):
    ss["wbgt_eff_c"] = ss["wbgt_base_frozen"]

# ---------------------------------------------------------------
# Display baseline metrics
# ---------------------------------------------------------------
st.subheader("Computed Baseline (No Penalties Applied)")
c1, c2, c3 = st.columns(3)
c1.metric("Natural Wet-Bulb", fmt_temp(twb_c, ss["units"]))
c2.metric("WBGT Raw", fmt_temp(wbgt_raw_c, ss["units"]))
c3.metric("Wind", f"{ws_ms:.1f} m/s" if ss["units"]=="metric" else f"{ms_to_mph(ws_ms):.1f} mph")

# ---------------------------------------------------------------
# Penalty presets (°C) — internal truth
# ---------------------------------------------------------------
PPE_PRESETS     = {"None":0.0, "Light":1.0, "Moderate":2.0, "Heavy":3.0}
VEHICLE_PRESETS = {"None":0.0, "Open":1.0, "Enclosed":2.0, "Poorly ventilated":3.0}
RADIANT_PRESETS = {"None":0.0, "Hot surfaces":2.0, "Direct radiant":4.0, "Extreme radiant":5.0}
ADHOC_PRESETS   = {"None":0.0, "Minor":1.0, "Moderate":2.0, "Severe":4.0}

st.markdown("## 🔥 Exposure Adjustments / Penalties")

def delta_label(dc: float) -> str:
    return f"{dc:.1f}°C" if ss["units"]=="metric" else f"{dc*9/5:.1f}°F"

def _ensure_number_follows_preset(preset_key: str, input_key: str, preset_c: float):
    """
    Streamlit widget keys 'remember' their values.
    So: when preset changes, we must force-reset the number_input state.
    """
    prev = ss.get(preset_key + "__prev", None)
    if prev != ss.get(preset_key, None):
        # preset changed -> force number_input to preset in *display units*
        if ss["units"] == "metric":
            ss[input_key] = float(preset_c)
        else:
            ss[input_key] = float(preset_c * 9/5)
        ss[preset_key + "__prev"] = ss.get(preset_key, None)

def number_delta(input_key: str) -> float:
    """
    Reads the number_input in display units, returns internal °C.
    """
    if ss["units"] == "metric":
        dc = st.number_input("", step=0.1, key=input_key)
        return float(dc)
    else:
        df = st.number_input("", step=0.1, key=input_key)
        return float(df) * 5/9

col1, col2, col3, col4 = st.columns(4)

# ---------------- PPE ----------------
with col1:
    st.subheader("Clothing / PPE")
    labels = {f"{k} (+{delta_label(v)})": float(v) for k, v in PPE_PRESETS.items()}
    choice = st.selectbox("", list(labels.keys()), key="ppe_preset")
    preset_c = float(labels[choice])

    _ensure_number_follows_preset("ppe_preset", "ppe_delta_input", preset_c)
    ss["pen_clo_c"] = number_delta("ppe_delta_input")

# ---------------- Vehicle ----------------
with col2:
    st.subheader("Vehicle / Enclosure")
    labels = {f"{k} (+{delta_label(v)})": float(v) for k, v in VEHICLE_PRESETS.items()}
    choice = st.selectbox("", list(labels.keys()), key="veh_preset")
    preset_c = float(labels[choice])

    _ensure_number_follows_preset("veh_preset", "veh_delta_input", preset_c)
    ss["pen_veh_c"] = number_delta("veh_delta_input")

# ---------------- Radiant ----------------
with col3:
    st.subheader("Radiant / Hot Surfaces")
    labels = {f"{k} (+{delta_label(v)})": float(v) for k, v in RADIANT_PRESETS.items()}
    choice = st.selectbox("", list(labels.keys()), key="rad_preset")
    preset_c = float(labels[choice])

    _ensure_number_follows_preset("rad_preset", "rad_delta_input", preset_c)
    ss["pen_rad_c"] = number_delta("rad_delta_input")

# ---------------- Adhoc ----------------
with col4:
    st.subheader("Ad-hoc / Site-specific")
    labels = {f"{k} (+{delta_label(v)})": float(v) for k, v in ADHOC_PRESETS.items()}
    choice = st.selectbox("", list(labels.keys()), key="adhoc_preset")
    preset_c = float(labels[choice])

    _ensure_number_follows_preset("adhoc_preset", "adhoc_delta_input", preset_c)
    ss["pen_adhoc_c"] = number_delta("adhoc_delta_input")

# ======================================================================
# BLOCK 5B — APPLY PENALTIES SAFELY (unit-aware, clamped, no negatives)
# ======================================================================

st.markdown("## 🚀 Apply Penalties & Compute WBGT-Effective")

if st.button("Apply adjustments & compute"):

    wbgt_base_c = ss.get("wbgt_base_frozen", None)  # use frozen baseline
    if wbgt_base_c is None:
        st.error("No frozen baseline WBGT available — set environmental inputs first.")
    else:
        # Values coming from UI are stored internally in °C
        ppe_c  = float(ss.get("pen_clo_c", 0.0))
        encl_c = float(ss.get("pen_veh_c", 0.0))
        rad_c  = float(ss.get("pen_rad_c", 0.0))
        ahoc_c = float(ss.get("pen_adhoc_c", 0.0))

        # Safety clamps per category
        ppe_c  = min(max(ppe_c,  0.0), 3.0)
        encl_c = min(max(encl_c, 0.0), 3.0)
        rad_c  = min(max(rad_c,  0.0), 5.0)
        ahoc_c = min(max(ahoc_c, 0.0), 4.0)

        total_penalty_c = ppe_c + encl_c + rad_c + ahoc_c
        total_penalty_c = min(total_penalty_c, 10.0)  # global cap

        wbgt_eff_c = wbgt_base_c + total_penalty_c

        ss["total_penalty_c"] = total_penalty_c
        ss["wbgt_eff_c"] = wbgt_eff_c
        ss["penalties_applied"] = True

        # Display with correct units
        if ss["units"] == "imperial":
            penalty_str = f"+{(total_penalty_c * 9/5):.1f} °F"
        else:
            penalty_str = f"+{total_penalty_c:.1f} °C"

        st.success(
            f"Penalties applied ({penalty_str}) → WBGT-effective = {fmt_temp(wbgt_eff_c, ss['units'])}. "
            "Scroll down for Heat-Stress Classification."
        )
# ======================================================================
# BLOCK 6 — NIOSH / OSHA WBGT THRESHOLDS (with Acclimatization Shift)
# ======================================================================

st.markdown("---")
st.markdown("## 🎯 Heat-Stress Thresholds (NIOSH / OSHA Reference)")

# Worker acclimatization toggle
accl_status = st.radio(
    "Worker acclimatization status",
    ["Acclimatized", "Not acclimatized"],
    horizontal=True,
    key="accl_status",
)

# Base threshold cut-points in °C (acclimatized reference from NIOSH guidance)
A_base = 29.0   # Info boundary
B_base = 32.0   # Caution boundary
C_base = 35.0   # Withdrawal boundary

# Adjustment for non-acclimatized workers (more conservative)
if accl_status == "Acclimatized":
    A, B, C = A_base, B_base, C_base
else:
    # shift downward by ~2°C for higher risk
    A, B, C = A_base - 2.0, B_base - 2.0, C_base - 2.0

# Store thresholds for classification block (correct keys)
ss["wbgt_A_c"] = A
ss["wbgt_B_c"] = B
ss["wbgt_C_c"] = C

# Also store in legacy keys (optional, for backward compatibility)
ss["thr_A_c"] = A
ss["thr_B_c"] = B
ss["thr_C_c"] = C

# Display outputs using user's selected units
colA, colB, colC = st.columns(3)
with colA:
    st.metric("Info threshold (A)", fmt_temp(A, ss["units"]))
with colB:
    st.metric("Caution (B)", fmt_temp(B, ss["units"]))
with colC:
    st.metric("Withdrawal (C)", fmt_temp(C, ss["units"]))

# Explanatory caption
if accl_status == "Acclimatized":
    st.caption(
        "These values approximate **NIOSH/OSHA heat-stress guidance** "
        "for acclimatized industrial workers."
    )
else:
    st.caption(
        "Thresholds automatically lowered for **non-acclimatized** workers "
        "(more conservative safety margin)."
    )
# ======================================================================
# BLOCK 7 — WBGT RISK CLASSIFICATION (POST-PENALTY)
# ======================================================================

st.markdown("## 🧭 Heat-Stress Classification & Worker Guidance")

wbgt_eff = ss.get("wbgt_eff_c", None)

if wbgt_eff is None:
    st.info("No computed WBGT value yet — apply adjustments and compute.")
else:
    A = ss["thr_A_c"]
    B = ss["thr_B_c"]
    C = ss["thr_C_c"]

    # Determine band
    if wbgt_eff < A:
        band = "Low environmental heat stress"
        colour = "🟢"
        msg = (
            "Suitable for normal operations. Maintain hydration and routine supervision."
        )
    elif wbgt_eff < B:
        band = "Heightened / Caution"
        colour = "🟠"
        msg = (
            "Increase supervision, enforce hydration, consider work–rest cycles."
        )
    elif wbgt_eff < C:
        band = "High strain warning"
        colour = "🔴"
        msg = (
            "Restrict exposure, enforce shortened work–rest cycles, "
            "actively cool workers, medical watch."
        )
    else:
        band = "Withdrawal / Stop Work"
        colour = "🚫"
        msg = (
            "Stop normal work. Only emergency tasks with strict controls "
            "and medical monitoring."
        )

    # Save for logging / export
    ss["risk_band"] = band

    # Display metrics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("WBGT (effective)", fmt_temp(wbgt_eff, ss["units"]))

    with col2:
        st.metric("Risk category", f"{colour} {band}")

    with col3:
        if ss["units"] == "metric":
            st.metric("Penalties applied", f"+{ss.get('total_penalty_c', 0):.1f} °C")
        else:
            st.metric("Penalties applied", f"+{(ss.get('total_penalty_c', 0) * 9/5):.1f} °F")

    st.markdown("### 👷 Supervisor Guidance")
    st.write(msg)

    # Optional CHSI dummy scaling (0–50)
    chsi_raw = wbgt_eff - 25.0   # placeholder
    chsi_scaled = max(0, min(50, (chsi_raw / 10) * 50))
    ss["chsi_scaled"] = chsi_scaled

    st.markdown("#### 🔬 CHSI surrogate (scaled 0–50)")
    if chsi_scaled < 15:
        st.success(f"CHSI {chsi_scaled:.0f} — low internal strain.")
    elif chsi_scaled < 30:
        st.warning(f"CHSI {chsi_scaled:.0f} — mild heat accumulation.")
    else:
        st.error(f"CHSI {chsi_scaled:.0f} — major heat strain risk!")

    st.caption(
        "CHSI here is an **internal heat-strain surrogate**, scaled for simplicity. "
        "Real CHSI requires physiology modelling."
    )

# ======================================================================
# BLOCK 8 — LOGGING OF COMPUTED DECISIONS (AUDIT TRAIL)
# ======================================================================

st.markdown("---")
st.markdown("## 📜 Heat-Stress Audit History")

# initialise log list in session.
if "audit_log" not in ss:
    ss["audit_log"] = []


# log only when a WBGT effective was just calculated
if ss.get("penalties_applied", False) and ss.get("wbgt_eff_c") is not None:

    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "location": ss.get("place_label", ""),
        "DB (°C)": f"{ss.get('db_c', 0):.1f}",
        "RH (%)": f"{ss.get('rh_pct', 0):.0f}",
        "GT (°C)": f"{ss.get('gt_c', 0):.1f}",
        "WBGT baseline (°C)": f"{ss.get('wbgt_base_c', 0):.1f}",
        "Penalty total (°C)": f"{ss.get('total_penalty_c', 0):.1f}",
        "WBGT eff (°C)": f"{ss.get('wbgt_eff_c', 0):.1f}",
        "Risk": ss.get("risk_band", ""),
        "CHSI scaled": f"{ss.get('chsi_scaled', 0):.0f}",
    }

    # Only append if it's not a duplicate of the last entry
    if not ss["audit_log"] or log_entry != ss["audit_log"][-1]:
        ss["audit_log"].append(log_entry)

# Display log table and export controls
has_log = bool(ss["audit_log"])
can_export = bool(ss.get("penalties_applied", False))

if has_log:
    df = pd.DataFrame(ss["audit_log"])
    st.dataframe(df, use_container_width=True)
    csv_data = df.to_csv(index=False).encode("utf-8")
else:
    st.info("No computed decisions yet. Records appear after computation.")
    csv_data = "".encode("utf-8")

st.download_button(
    label="📥 Download Audit Log as CSV",
    data=csv_data,
    file_name=f"CHSRMT_Audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
    mime="text/csv",
    disabled=not can_export,
)

# Display log table
# if ss["audit_log"]:
  #  df = pd.DataFrame(ss["audit_log"])
   # st.dataframe(df, use_container_width=True)

    # ---- CSV Export ----
    # csv_data = df.to_csv(index=False).encode("utf-8")
    # st.download_button(
      #  label="📥 Download Audit Log as CSV",
       # data=csv_data,
        # file_name=f"CHSRMT_Audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        # mime="text/csv",
    # )

# else:
  #  st.info("No computed decisions yet.")
# ==============================================================
# BLOCK 9 — APPENDIX & FIELD GUIDANCE (COLLAPSIBLE)
# ==============================================================

st.markdown("---")
st.markdown("## 📘 Field Appendix — Hydration, Acclimatization, Work–Rest & Warning Signs")

with st.expander("🥤 Hydration Guidance (General Field Advice)"):
    st.markdown("""
    **Suggested quantities (moderate work)**  
    - 250–500 mL every **20 minutes** (≈ ¾–1 US pint per 20 minutes)  
    - Avoid > 1.5 L/hour (risk of hyponatremia)  
    - Include **electrolytes every 2–3 hours**
    
    **Avoid**
    - Alcohol before work  
    - Excessive caffeine  
    - Energy drinks as fluid replacement
    
    **Warning signs of dehydration**
    - Thirst, dry mouth  
    - Dark yellow urine  
    - Headache, fatigue  
    - Cramps
    """)

with st.expander("⚡ Acclimatization Expectations (OSHA/NIOSH style)"):
    st.markdown("""
    **Typical timeline**
    - 5–7 shifts of increasing exposure  
    - Begin at **20% of usual duration** on day 1, add **20% per day**
    
    **High-risk when**
    - New workers  
    - Returning after > 1 week absence  
    - Workers recently ill
    
    **Supervision**
    - Mandatory buddy system during first 1–3 days  
    - Observe for confusion or loss of coordination
    """)

with st.expander("⏱ Work–Rest / Supervision Prompts"):
    st.markdown("""
    These prompts should guide **field supervisors**, not replace policy.
    
    **When in Green Zone**
    - Routine work  
    - Encourage fluids  
    - Normal supervision
    
    **Amber Zone**
    - Enforce breaks  
    - Actively monitor symptoms  
    - Provide shade
    
    **Red / Withdrawal Zone**
    - Stop routine work  
    - Only emergency tasks with medical oversight  
    - Mandatory cooling interventions
    """)

with st.expander("🚩 Early Warning Signs & First-Aid Triggers"):
    st.markdown("""
    **Red-flag symptoms requiring immediate action**
    - Dizziness, collapse, faintness  
    - Confusion or altered behavior  
    - Vomiting  
    - Hot, red, dry skin  
    - Staggering movement
    
    **Immediate steps**
    - Move to shade/cooling  
    - Apply cool water or packs to neck/axilla/groin  
    - Provide fluids if conscious  
    - Activate emergency medical support if no rapid improvement
    """)

with st.expander("🏥 Common Medical End-points (for HSE orientation)"):
    st.markdown("""
    **Heat Exhaustion**
    - Sweating, nausea, rapid pulse  
    - Elevated temperature but < 40°C (104°F)  
    - Requires fluid replacement & monitoring
    
    **Heat Stroke**
    - Core temperature ≥ 40°C (≥104°F)  
    - CNS dysfunction (confusion, seizure, coma)  
    - **Medical emergency — activate EMS**
    """)

st.markdown("---")
st.caption("This appendix provides field-support content only. It does **not replace medical assessment, OSHA/NIOSH procedures, or employer HSE policy.**")
