# app.py
# Streamlit Turkish Folk Fret Calculator (kısa sap bağlama – alt tel)
# Features:
# - Inputs: reference frequency (Hz), string length (any unit)
# - Editable pitch order (supports tokens like "mi b2", "fa#3", "do #")
# - Turkish folk comma presets (b, b2, #3) + AEU-ish and 24-EDO examples
# - Safe octave handling (small backsteps don't wrap; true wraps add +1200c)
# - CSV download
# - Optional second tuning panel to compare side-by-side

import math
from typing import List, Tuple, Dict
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Turkish Folk Fret Calculator", layout="wide")

# -----------------------------
# Defaults
# -----------------------------
DEFAULT_REF_HZ = 440.0     # open string Re = 440 Hz
DEFAULT_SCALE  = 580.0     # string length (e.g., 580 mm)
DEFAULT_ORDER  = (
    "mi b2, mi b, mi,\n"
    "fa, fa#3, fa#,\n"
    "sol, sol#3, sol#,\n"
    "la,\n"
    "si b2, si b, si,\n"
    "do, do #3, do #,\n"
    "re,\n"
    "mi b2, mi b, mi"
)

# -----------------------------
# Accidental (comma) presets (cents)
# b  = -22.64  (one comma)
# b2 = -45.28  (two commas)
# #3 = +67.92  (three commas sharp)
# Extras are supported by parser but the UI focuses on these three.
# -----------------------------
PRESET_CENTS: Dict[str, Dict[str, float]] = {
    "Folk (b=-22.64, b2=-45.28, #3=+67.92)": {
        "b": -22.64,
        "b2": -45.28,
        "#3": 67.92,
    },
    "AEU ~53-comma (≈22.64 c per comma)": {
        # Using the same base comma size for illustration; adjust here if your institution uses different calibration
        "b": -22.64,
        "b2": -45.28,
        "#3": 3 * 22.64,
    },
    "24-EDO (quarter-tone approx)": {
        # Quarter-tone grid: 50 c per step; #3 interpreted as +150 c here
        "b": -50.0,
        "b2": -100.0,
        "#3": 150.0,
    },
}

# Complete table used internally (keeps extra accidentals available)
DEFAULT_CENTS_ALL: Dict[str, float] = {
    "":     0.00,   # natural
    "b":   -22.64,
    "b1":  -22.64,  # alias
    "b2":  -45.28,
    "#3":   67.92,
    # optional extras
    "#":   100.00,
    "#1":   22.64,
    "#2":   45.28,
    "#5":  113.20,
    "b3":  -67.92,
    "b4":  -90.57,
}

# -----------------------------
# Base note positions (cents) with Re = 0
# Re(D)=0, Mi=+200, Fa=+300, Fa#=+400, Sol=+500, Sol#=+600,
# La=+700, Sib(Bb)=+800, Si(B)=+900, Do=+1000, Do#=+1100, Re=+1200 ...
# -----------------------------
BASE_FROM_RE: Dict[str, int] = {
    "re":   0,
    "mi":   200,
    "fa":   300,
    "fa#":  400,
    "sol":  500,
    "sol#": 600,
    "la":   700,
    "sib":  800,   # Bb (La#)
    "si":   900,
    "do":   1000,
    "do#":  1100,
}

# -----------------------------
# Math helpers
# -----------------------------

def cents_to_ratio(c: float) -> float:
    return 2.0 ** (c / 1200.0)

def freq_from_open(f_open: float, cents_from_open: float) -> float:
    return f_open * cents_to_ratio(cents_from_open)

def nut_to_fret_distance(scale_length: float, cents_from_open: float) -> float:
    # L = L0 / 2^(c/1200); d = L0 - L = L0 * (1 - 2^(-c/1200))
    return scale_length * (1.0 - (2.0 ** (-cents_from_open / 1200.0)))

def parse_token(tok: str) -> Tuple[str, str]:
    """
    Parse tokens like:
      'mi b'  -> ('mi', 'b')
      'mi b2' -> ('mi', 'b2')
      'fa#3'  -> ('fa', '#3')
      'do #'  -> ('do', '#')
      'si'    -> ('si', '')
      'sib'   -> ('sib','')  (alias for 'si b')
    """
    t = tok.strip().lower().replace("  ", " ")
    t = t.replace("♯", "#").replace("♭", "b")

    if t in ("sib", "si b", "si bb"):
        return ("sib", "")

    if " " in t:
        base, acc = t.split()
        return (base, acc)

    for tag in ["#5", "#3", "#2", "#1", "#", "b4", "b3", "b2", "b1", "b"]:
        if t.endswith(tag):
            return (t[: -len(tag)], tag)

    return (t, "")

def base_cents(base: str) -> int:
    if base in BASE_FROM_RE:
        return BASE_FROM_RE[base]
    raise KeyError(f"Unknown base note: '{base}'")


def parse_order(text: str) -> List[str]:
    parts: List[str] = []
    for line in text.split("\n"):
        for seg in line.split(","):
            s = seg.strip()
            if s:
                parts.append(s)
    return parts


def build_rows(order_list: List[str],
               f_open: float,
               scale_len: float,
               cents_table: Dict[str, float],
               small_backstep_tol: float = 100.0) -> pd.DataFrame:
    """
    Build rows for the given pitch order.
    Small local down-steps do not force an octave bump.
    True wrap-around gets +1200 cents.
    """
    rows = []
    last_shifted = -1e9
    shift = 0.0
    idx = 0

    for token in order_list:
        base, acc = parse_token(token)
        base_c = BASE_FROM_RE["sib"] if base == "sib" else base_cents(base)
        if acc not in cents_table:
            raise KeyError(f"Unknown accidental '{acc}' in token '{token}'")
        acc_c = cents_table[acc]

        unshifted = base_c + acc_c
        proposed = unshifted + shift

        if proposed < last_shifted - small_backstep_tol:
            shift += 1200.0
            proposed = unshifted + shift

        freq = freq_from_open(f_open, proposed)
        dist = nut_to_fret_distance(scale_len, proposed)

        idx += 1
        rows.append({
            "#": idx,
            "pitch": token,
            "cents_from_re": round(proposed, 3),
            "frequency_hz": round(freq, 5),
            "nut_to_fret": round(dist, 3),
        })
        last_shifted = proposed

    return pd.DataFrame(rows, columns=["#", "pitch", "cents_from_re", "frequency_hz", "nut_to_fret"])  # type: ignore


# -----------------------------
# UI
# -----------------------------

st.title("Turkish Folk Fret Calculator (Streamlit)")
st.caption("Re (open string) is the reference at 0 cents. Octave wrap occurs after large backward jumps only.")

with st.sidebar:
    st.subheader("Inputs")
    ref_hz = st.number_input("Reference frequency (open string, Hz)", min_value=0.01, value=DEFAULT_REF_HZ, step=0.01)
    scale_len = st.number_input("String length (your unit; output same unit)", min_value=0.01, value=DEFAULT_SCALE, step=0.01)

    st.divider()
    st.subheader("Comma presets")
    preset_name = st.selectbox("Preset", list(PRESET_CENTS.keys()))

    # Maintain a full table internally so extra symbols still work
    cents_table = dict(DEFAULT_CENTS_ALL)

    # Apply preset values to the three primary comma fields
    preset_vals = PRESET_CENTS[preset_name]
    b_val  = st.number_input("b (cents)",  value=float(preset_vals["b"]),  step=0.01, format="%.2f")
    b2_val = st.number_input("b2 (cents)", value=float(preset_vals["b2"]), step=0.01, format="%.2f")
    s3_val = st.number_input("#3 (cents)", value=float(preset_vals["#3"]), step=0.01, format="%.2f")

    # Mirror into the working table (keep aliases consistent)
    cents_table["b"]  = b_val
    cents_table["b1"] = b_val
    cents_table["b2"] = b2_val
    cents_table["#3"] = s3_val

st.subheader("Pitch order (comma- or newline-separated)")
if "order_text" not in st.session_state:
    st.session_state.order_text = DEFAULT_ORDER

# Preset orders
ORDER_PRESETS: Dict[str, str] = {
    "Lower string (corrected, flatter→sharper)": DEFAULT_ORDER,
    "Naturals up to octave": "mi, fa, fa#, sol, sol#, la, si, do, do#, re, mi",
}

c1, c2 = st.columns([2,1])
with c1:
    order_text = st.text_area(" ", value=st.session_state.order_text, height=170, label_visibility="collapsed")
with c2:
    order_choice = st.selectbox("Order preset", list(ORDER_PRESETS.keys()))
    if st.button("Apply order preset"):
        st.session_state.order_text = ORDER_PRESETS[order_choice]
        st.experimental_rerun()

# Action buttons
bcols = st.columns([1,1,3])
with bcols[0]:
    compute = st.button("Compute", type="primary")
with bcols[1]:
    reset = st.button("Reset")

if reset:
    for k in ("order_text",):
        if k in st.session_state:
            del st.session_state[k]
    st.experimental_rerun()

if compute or True:
    try:
        order_list = parse_order(st.session_state.get("order_text", DEFAULT_ORDER))
        df = build_rows(order_list, ref_hz, scale_len, cents_table)
        st.success(f"Computed {len(df)} rows. First: {df.iloc[0]['cents_from_re']} c • Last: {df.iloc[-1]['cents_from_re']} c")
        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download CSV", csv, file_name="turkish_fret_calculator.csv", mime="text/csv")
        st.caption("‘Nut → Fret’ uses the same unit as your string length.")
    except Exception as e:
        st.error(str(e))

st.divider()

# Optional second tuning comparison
with st.expander("Compare a second tuning / string"):
    cA, cB, cC = st.columns(3)
    with cA:
        ref_hz2 = st.number_input("Ref Hz (2)", min_value=0.01, value=DEFAULT_REF_HZ, step=0.01, key="ref2")
    with cB:
        scale_len2 = st.number_input("String length (2)", min_value=0.01, value=DEFAULT_SCALE, step=0.01, key="L2")
    with cC:
        order_text2 = st.text_area("Order (2)", value=DEFAULT_ORDER, height=120, key="ord2")

    # share comma table with first for now; you can add a separate preset if desired
    if st.button("Compute (2)"):
        try:
            order_list2 = parse_order(order_text2)
            df2 = build_rows(order_list2, ref_hz2, scale_len2, cents_table)
            st.dataframe(df2, use_container_width=True)
            csv2 = df2.to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV (2)", csv2, file_name="turkish_fret_calculator_2.csv", mime="text/csv")
        except Exception as e:
            st.error(str(e))
