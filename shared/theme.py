from __future__ import annotations

import streamlit as st


def apply_theme() -> None:
    st.markdown(
        """
<style>
:root {
  --vdb-bg: #ffffff;
  --vdb-panel: #ffffff;
  --vdb-panel-2: #f7f7f7;
  --vdb-border: rgba(17,17,17,.12);
  --vdb-text: #111111;
  --vdb-muted: rgba(17,17,17,.65);
  --vdb-accent: #111111;
  --vdb-accent-2: #4d4d4d;
  --vdb-good: #0f9d58;
  --vdb-warn: #c28a00;
}

/* ---------- Main Page ---------- */

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background: var(--vdb-bg) !important;
    color: var(--vdb-text) !important;
}

.stApp {
    background: var(--vdb-bg) !important;
    color: var(--vdb-text) !important;
}

.block-container {
    padding-top: 2.25rem !important;
    padding-bottom: 3rem;
    max-width: 1450px;
}

[data-testid="stMarkdownContainer"],
[data-testid="stText"],
label,
p,
h1,
h2,
h3,
h4,
h5,
h6 {
    color: var(--vdb-text);
}

/* ---------- Sidebar ---------- */

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #ffffff 0%, #f6f6f6 100%);
    border-right: 1px solid var(--vdb-border);
}

/* Shrink the default header area so the brand sits closer to the top */
[data-testid="stSidebarHeader"] {
    min-height: 0 !important;
    padding-top: 0.25rem !important;
    padding-bottom: 0 !important;
}

[data-testid="stSidebarUserContent"] {
    padding-top: 0 !important;
}

[data-testid="stSidebar"] .block-container {
    padding-top: 0 !important;
}

/* Pull the custom brand block upward slightly to offset Streamlit spacing */
.vdb-sidebar-brand {
    margin-top: -1.9rem;
    text-align: center;
    width: 100%;
}

/* Remove any extra margin from the first sidebar element */
[data-testid="stSidebar"] .element-container:first-child {
    margin-top: 0 !important;
    padding-top: 0 !important;
}

/* Remove image margin */
[data-testid="stSidebar"] img {
    margin-top: 0 !important;
    display: block;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: var(--vdb-muted);
}

/* ---------- Inputs ---------- */

[data-baseweb="tag"] {
  background: #111111 !important;
  border-radius: 10px !important;
}

[data-baseweb="tag"] *,
[data-baseweb="tag"] span,
[data-baseweb="tag"] div {
  color: #ffffff !important;
}

[data-baseweb="select"] > div {
  background: #ffffff !important;
  color: #111111 !important;
  border-color: rgba(17,17,17,.16) !important;
}

/* ---------- Metrics ---------- */

[data-testid="stMetric"] {
  background: var(--vdb-panel);
  border: 1px solid var(--vdb-border);
  border-radius: 18px;
  padding: 1rem;
  box-shadow: 0 10px 28px rgba(0,0,0,.06);
}

/* ---------- Buttons ---------- */

.stButton > button,
.stDownloadButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"] {
  border-radius: 14px !important;
  min-height: 2.75rem;
  font-weight: 700 !important;
}

.stButton > button,
.stDownloadButton > button,
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-primary"] {
  background: #ffffff !important;
  color: #111111 !important;
  border: 1px solid rgba(17,17,17,.16) !important;
  box-shadow: none !important;
}

.stButton > button:hover,
.stDownloadButton > button:hover,
[data-testid="stBaseButton-secondary"]:hover,
[data-testid="stBaseButton-primary"]:hover {
  background: #f3f3f3 !important;
  border-color: rgba(17,17,17,.3) !important;
}

/* ---------- Hero ---------- */

.vdb-hero {
  position: relative;
  overflow: hidden;
  border: 1px solid var(--vdb-border);
  background:
    radial-gradient(circle at top left, rgba(0,0,0,.045), transparent 35%),
    radial-gradient(circle at bottom right, rgba(0,0,0,.03), transparent 35%),
    linear-gradient(135deg, #ffffff, #f4f4f4);
  border-radius: 28px;
  padding: 2rem 2.1rem;
  margin-bottom: 1.15rem;
  box-shadow: 0 24px 70px rgba(0,0,0,.08);
}

.vdb-hero h1 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3.5rem);
  line-height: 1;
  letter-spacing: -.06em;
}

.vdb-hero p {
  margin: .75rem 0 0;
  color: var(--vdb-muted);
  font-size: 1.02rem;
  max-width: 880px;
}

.vdb-hero .vdb-badge-row {
  margin-top: 1rem;
  display: flex;
  gap: .5rem;
  flex-wrap: wrap;
}

/* ---------- Pills ---------- */

.vdb-pill {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  border: 1px solid var(--vdb-border);
  background: #f5f5f5;
  border-radius: 999px;
  padding: .32rem .7rem;
  color: var(--vdb-text);
  font-size: .82rem;
  font-weight: 700;
}

/* ---------- Cards ---------- */

.vdb-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 1rem;
}

@media (max-width:1050px){
  .vdb-grid{
    grid-template-columns:repeat(2,minmax(0,1fr));
  }
}

@media (max-width:680px){
  .vdb-grid{
    grid-template-columns:1fr;
  }
}

.vdb-card {
  border: 1px solid var(--vdb-border);
  background: linear-gradient(180deg, #ffffff, #fafafa);
  border-radius: 22px;
  padding: 1.05rem;
  min-height: 182px;
  box-shadow: 0 14px 42px rgba(0,0,0,.06);
}

.vdb-card:hover {
  border-color: rgba(17,17,17,.32);
  transform: translateY(-1px);
  transition: all .16s ease;
}

.vdb-card-top {
  display:flex;
  justify-content:space-between;
  gap:.75rem;
  align-items:flex-start;
}

.vdb-icon {
  width:42px;
  height:42px;
  border-radius:15px;
  display:flex;
  align-items:center;
  justify-content:center;
  background:linear-gradient(135deg,#f7f7f7,#ececec);
  border:1px solid var(--vdb-border);
  font-size:1.25rem;
}

.vdb-card h3{
  margin:.75rem 0 .35rem;
  font-size:1.05rem;
  letter-spacing:-.02em;
}

.vdb-card p{
  margin:0;
  color:var(--vdb-muted);
  font-size:.9rem;
  line-height:1.42;
  min-height:3.8rem;
}

.vdb-card-footer{
  margin-top:.9rem;
  display:flex;
  gap:.4rem;
  flex-wrap:wrap;
}

.vdb-status{
  font-size:.75rem;
  padding:.2rem .55rem;
  border-radius:999px;
  border:1px solid var(--vdb-border);
  color:var(--vdb-text);
}

.status-built-in{
  background:rgba(15,157,88,.12);
  border-color:rgba(15,157,88,.28);
}

.status-ready{
  background:rgba(17,17,17,.06);
  border-color:rgba(17,17,17,.18);
}

.status-linked{
  background:rgba(194,138,0,.08);
  border-color:rgba(194,138,0,.24);
}

.vdb-section-title{
  margin:1.4rem 0 .8rem;
  display:flex;
  align-items:center;
  justify-content:space-between;
}

.vdb-section-title h2{
  margin:0;
  font-size:1.25rem;
}

.vdb-muted{
  color:var(--vdb-muted);
}

.vdb-command{
  border:1px solid var(--vdb-border);
  background:#f7f7f7;
  border-radius:18px;
  padding:1rem;
}

.vdb-mini-row{
  display:grid;
  grid-template-columns:1fr 1fr;
  gap:1rem;
}

@media(max-width:800px){
  .vdb-mini-row{
      grid-template-columns:1fr;
  }
}

.vdb-timeline{
  border-left:2px solid rgba(17,17,17,.18);
  margin-left:.45rem;
  padding-left:1rem;
}

.vdb-step{
  margin-bottom:1rem;
}

.vdb-step b{
  color:var(--vdb-text);
}

.vdb-step span{
  display:block;
  color:var(--vdb-muted);
  font-size:.9rem;
  margin-top:.1rem;
}
</style>
        """,
        unsafe_allow_html=True,
    )
