import streamlit as st
import pandas as pd
from pathlib import Path

THEMES = {
    "Funds, KYC & Account Access": ["withdraw", "bank credit", "debited", "kyc", "verification", "login", "otp", "account"],
    "Orders & Trading": ["order", "trade execution", "exit a position", "profit/loss", "f&o"],
    "App Experience & Reliability": ["app", "slow", "freeze", "crash", "dashboard", "update", "taps"],
    "Support & Communications": ["support", "ticket", "notification", "promotional", "messages"],
    "Product Requests": ["goal-wise", "customize", "tracker"],
}
def classify(t):
    t = str(t).lower()
    scores = {k: sum(x in t for x in kws) for k,kws in THEMES.items()}
    k=max(scores,key=scores.get)
    return k if scores[k] else "Other"

st.set_page_config(page_title="Groww Review Pulse", layout="wide")
st.title("Groww — Weekly Review Pulse")
st.caption("LIP 5 prototype · public-review CSV → themes → quotes → actions → email draft")

uploaded = st.file_uploader("Upload public review export CSV", type="csv")
if uploaded:
    df = pd.read_csv(uploaded)
else:
    demo = Path("data/reviews_demo.csv")
    if demo.exists():
        df = pd.read_csv(demo)
        st.info("Using demo/sample corpus. Replace it with your public export for a real weekly run.")
    else:
        st.stop()

required={"source","date","rating","text"}
missing=required-set(df.columns)
if missing:
    st.error(f"Missing columns: {', '.join(sorted(missing))}")
    st.stop()

df["date"]=pd.to_datetime(df["date"], errors="coerce")
df=df.dropna(subset=["date","text"])
df["theme"]=df["text"].map(classify)

week = st.date_input("Week ending", value=df["date"].max().date())
window_start = pd.Timestamp(week) - pd.Timedelta(days=6)
w=df[(df["date"]>=window_start)&(df["date"]<=pd.Timestamp(week))].copy()
if w.empty: w=df.copy()

counts=w["theme"].value_counts()
st.metric("Reviews in selected week", len(w))
st.subheader("Top 3 themes")
for i,(theme,n) in enumerate(counts.head(3).items(),1):
    st.write(f"**{i}. {theme}** — {n} reviews")

st.subheader("3 user quotes")
for _,r in w.sort_values(["rating","date"], ascending=[True,False]).head(3).iterrows():
    st.write(f'“{r["text"]}” — {int(r["rating"])}★, {r["source"]}, {r["date"].date()}')

st.subheader("3 action ideas")
actions=[
    "Add clearer withdrawal status and expected-credit timing.",
    "Add order-execution diagnostics and a visible retry/status state.",
    "Test goal-wise portfolio tracking with customizable buckets."
]
for a in actions: st.write("• "+a)

st.download_button("Download weekly note", 
    "GROWW — WEEKLY REVIEW PULSE\n\n" + "\n".join([f"{i}. {t} — {n} reviews" for i,(t,n) in enumerate(counts.head(3).items(),1)]),
    file_name="weekly_pulse.txt")
