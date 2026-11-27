# =====================================================================
#  Camel NBFC Analytics - Company Website (Streamlit)
#  Developed by camel_nbfc_analytics_solution
# ---------------------------------------------------------------------
#  Tabs : Home · About · Products · Contact
#  - Products only SHOWCASES our services (no app code inside).
#  - "Book a free demo" / "Request a demo" -> opens a demo-booking form (pop-up)
#  - "Talk to us"                          -> opens a quick message form (pop-up)
#  - Every form submission (demo / talk / contact) is sent to:
#       1) E-mail  -> camelnbfcanalytics@gmail.com  (Gmail SMTP, needs [email] secrets)
#       2) Google Sheet (permanent record, works on Streamlit Cloud, needs [sheet] secrets)
#       3) Local CSV  camel_contact_submissions.csv  (only permanent on your own PC / VM)
#  - Admin page: open  <site-url>/?admin=1  -> enquiries + "Send test e-mail" button.
#
#  Secrets: local  -> .streamlit/secrets.toml
#           Cloud  -> Streamlit Cloud > App > Settings > Secrets
#
#  Install : pip install streamlit pandas
#  Run     : streamlit run camel_website.py --server.port 8501
# =====================================================================

import html as htmllib
import json
import re
import smtplib
import ssl
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------
# 1. SITE CONFIG  (edit here only)
# ---------------------------------------------------------------------
BRAND = "Camel NBFC Analytics"
TAGLINE = "Risk analytics solutions for NBFCs, MFIs & HFCs"
DEVELOPER = "camel_nbfc_analytics_solution"
CONTACT_EMAIL = "camelnbfcanalytics@gmail.com"   # e-mail shown on the website
NOTIFY_EMAIL = "camelnbfcanalytics@gmail.com"                     # e-mail that RECEIVES every enquiry
CONTACT_PHONE = ""                                # add later - blank shows "Will be updated soon"
CONTACT_ADDRESS = "Shop No. 3, Nitayanand Nagar, Ghatkopar West, Mumbai - 400086"
WORKING_HOURS = "Mon - Sat · 10:00 - 18:30 IST"
LINKEDIN_URL = ""                                 # optional
NEWS_APP_URL = ""                                 # optional - public link of Risk Daily News FK
CONTACT_FILE = Path(__file__).parent / "camel_contact_submissions.csv"

IST = timezone(timedelta(hours=5, minutes=30))   # Streamlit Cloud runs in UTC - always stamp in IST


def now_ist() -> datetime:
    return datetime.now(IST).replace(tzinfo=None)


PHONE_TEXT = CONTACT_PHONE if CONTACT_PHONE.strip() else "Will be updated soon"

# Column order of the enquiries (CSV + Google Sheet use the same columns)
ENQUIRY_COLUMNS = ["submitted_at", "enquiry_type", "name", "email", "organisation", "phone",
                   "interest", "preferred_date", "preferred_time", "contact_mode", "message"]

DEMO_SLOTS = ["10:00 - 11:00", "11:00 - 12:00", "12:00 - 13:00", "14:00 - 15:00",
              "15:00 - 16:00", "16:00 - 17:00", "17:00 - 18:00"]

# Current services shown to clients (add new services here later)
SERVICES = [
    dict(icon="🧮", name="Risk Analytics Studio", status="Available", cls="live",
         text="A ready-to-use risk analytics application. Upload your loan data and get Static Pool, Roll Rate, "
              "QMA, Non-Starter, Fraud EWS, PAR and Collection Efficiency analysis with colour dashboards and Excel reports.",
         points=["7 risk modules in one application", "No database connection - CSV / Excel upload",
                 "Auto column mapping & data templates", "One-click Excel report per module"],
         link=""),
    dict(icon="📰", name="Risk Daily News FK", status="Live", cls="live",
         text="A daily risk-news dashboard for Indian microfinance, MFI / JLG / SHG, NBFC, regulation and "
              "climate-risk events - so risk teams see what matters every morning.",
         points=["Sector-focused news from multiple sources", "Risk categories & search",
                 "Excludes general bank / stock-market noise", "Refreshed daily"],
         link=NEWS_APP_URL),
    dict(icon="⚙️", name="Business Rule Engine (BRE)", status="Available on request", cls="dev",
         text="Configurable credit-decision rules between LOS and LMS, with an admin console to manage "
              "rules and users and a secure REST API for integration.",
         points=["Rule master with versioning tags", "Admin console for rules & users",
                 "REST API with API-key authentication", "Supports multiple lending entities"],
         link=""),
]
SERVICE_NAMES = [s["name"] for s in SERVICES]

# Risk Analytics Studio modules - showcase text only (the app itself is sold separately)
STUDIO_MODULES = [
    ("📊", "Static Pool (Vintage)", "Delinquency of each disbursement cohort by months-on-book, as heatmap and vintage curves."),
    ("🔄", "Roll Rate", "Month-on-month movement between DPD buckets - forward roll, stable, cure and closed."),
    ("⏱️", "QMA (Early Mortality)", "Share of loans crossing DPD > 30 within the first months on book, by cohort."),
    ("🚫", "Non-Starter", "Loans that never paid an instalment after the first EMI fell due."),
    ("🛡️", "Fraud EWS", "Rule-based early-warning score for possible fraud / proxy lending patterns."),
    ("📈", "PAR & Bucket Health", "PAR 1/30/60/90, DPD bucket mix, trend and geography concentration."),
    ("💰", "Collection Efficiency", "Demand vs collection, current and overall CE % against target by branch."),
]

# ---------------------------------------------------------------------
# 2. STYLE  (full-width layout, professional navy / blue palette)
# ---------------------------------------------------------------------
SITE_CSS = """
<style>
:root{--navy:#0F2747;--navy2:#163A66;--blue:#1F5FA8;--sky:#9CC3F0;--ink:#1E293B;--muted:#64748B;--line:#E2E8F0;--bg:#F5F7FA;}
/* full width page + hide Streamlit's own toolbar / menu (site looks like a normal website) */
.stApp{background:var(--bg);}
header[data-testid="stHeader"]{display:none;}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"]{display:none !important;}
.block-container{max-width:100% !important;padding:0 2.5rem 0 2.5rem !important;}

/* ---------- top navigation bar ---------- */
.fk-nav{background:var(--navy);margin:0 -2.5rem;padding:12px 2.5rem;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;border-bottom:3px solid var(--blue);}
.fk-brand{display:flex;align-items:center;gap:12px;}
.fk-logo{width:44px;height:44px;border-radius:11px;background:#fff;display:flex;align-items:center;justify-content:center;font-size:24px;box-shadow:0 2px 6px rgba(0,0,0,.2);}
.fk-name{font-weight:800;color:#fff;font-size:1.25rem;line-height:1.1;letter-spacing:.01em;}
.fk-name span{color:var(--sky);}
.fk-tag{color:#B8C7DB;font-size:.8rem;margin-top:2px;}
.fk-nav-right{display:flex;align-items:center;gap:18px;flex-wrap:wrap;}
.fk-nav-info{color:#CBD5E1;font-size:.82rem;}
.fk-nav-info b{color:#fff;font-weight:600;}
.fk-btn{display:inline-block;background:var(--blue);color:#fff !important;text-decoration:none !important;padding:9px 18px;border-radius:8px;font-weight:600;font-size:.88rem;border:1px solid var(--blue);cursor:pointer;}
.fk-btn:hover{background:#174C88;}
.fk-btn.ghost{background:transparent;border:1px solid rgba(255,255,255,.6);}
.fk-btn.ghost:hover{background:rgba(255,255,255,.12);}
.fk-btn.light{background:#fff;color:var(--navy) !important;border-color:#fff;}
.fk-btn.light:hover{background:#E8F0FA;}

/* ---------- hero ---------- */
.fk-hero{margin:0 -2.5rem 22px -2.5rem;padding:64px 2.5rem 70px 2.5rem;color:#fff;
  background:radial-gradient(circle at 85% 20%, rgba(156,195,240,.25) 0, transparent 40%),
             linear-gradient(120deg,#0F2747 0%,#163A66 55%,#1F5FA8 100%);}
.fk-hero-grid{display:grid;grid-template-columns:1.5fr 1fr;gap:40px;align-items:center;}
.fk-eyebrow{display:inline-block;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:4px 12px;font-size:.78rem;color:#E2E8F0;margin-bottom:14px;}
.fk-hero h1{color:#fff;font-size:2.8rem;line-height:1.15;margin:0 0 14px 0;font-weight:800;padding:0;}
.fk-hero h1 span{color:var(--sky);}
.fk-hero p{color:#D6E2F0;font-size:1.08rem;max-width:720px;margin:0 0 24px 0;}
.fk-hero .fk-btn{margin:0 10px 8px 0;}
.fk-hero-card{background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.2);border-radius:16px;padding:22px;}
.fk-hero-card h4{color:#fff;margin:0 0 12px 0;font-size:1rem;}
.fk-hero-card .row{display:flex;align-items:center;gap:10px;color:#E2E8F0;font-size:.9rem;padding:8px 0;border-bottom:1px solid rgba(255,255,255,.12);}
.fk-hero-card .row:last-child{border-bottom:none;}
.fk-hero-card .dot{width:8px;height:8px;border-radius:50%;background:#4ADE80;flex-shrink:0;}

/* ---------- tabs as a page menu ---------- */
.stTabs [data-baseweb="tab-list"]{gap:4px;flex-wrap:wrap;background:#fff;border:1px solid var(--line);border-radius:12px;padding:6px;box-shadow:0 1px 3px rgba(15,23,42,.05);}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:8px;padding:8px 18px;height:auto;}
.stTabs [data-baseweb="tab"] p{color:#475569;font-weight:600;font-size:.95rem;}
.stTabs [data-baseweb="tab"]:hover{background:#F1F5F9;}
.stTabs [aria-selected="true"]{background:var(--navy);}
.stTabs [aria-selected="true"] p{color:#fff !important;}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"]{display:none;}

/* ---------- content blocks ---------- */
.fk-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:18px 0;}
.fk-stat{background:#fff;border:1px solid var(--line);border-top:4px solid var(--blue);border-radius:12px;padding:16px;text-align:center;}
.fk-stat .n{font-size:1.7rem;font-weight:800;color:var(--navy);}
.fk-stat .t{font-size:.82rem;color:var(--muted);}
.fk-h2{font-size:1.55rem;font-weight:800;color:var(--navy);margin:28px 0 4px 0;}
.fk-sub{color:var(--muted);margin:0 0 14px 0;font-size:.97rem;}
.fk-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-bottom:10px;}
.fk-card{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:0 1px 3px rgba(15,23,42,.05);transition:transform .15s ease, box-shadow .15s ease;}
.fk-card:hover{transform:translateY(-3px);box-shadow:0 10px 22px rgba(15,39,71,.10);}
.fk-card .ic{font-size:1.7rem;}
.fk-card h3{font-size:1.06rem;color:var(--navy);margin:8px 0 6px 0;padding:0;}
.fk-card p{color:#475569;font-size:.9rem;margin:0;}
.pill{display:inline-block;font-size:.72rem;font-weight:700;border-radius:20px;padding:3px 10px;}
.pill.live{background:#DCFCE7;color:#166534;}.pill.dev{background:#FEF3C7;color:#92400E;}.pill.soon{background:#E2E8F0;color:#334155;}
.fk-svc{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px;margin-bottom:10px;}
.fk-svc-card{background:#fff;border:1px solid var(--line);border-top:5px solid var(--blue);border-radius:14px;padding:22px;box-shadow:0 1px 3px rgba(15,23,42,.05);display:flex;flex-direction:column;}
.fk-svc-card.soon{border-top-color:#94A3B8;background:#F8FAFC;border-style:dashed;}
.fk-svc-card .no{font-size:.72rem;color:var(--muted);font-weight:700;letter-spacing:.06em;text-transform:uppercase;}
.fk-svc-card h3{font-size:1.22rem;color:var(--navy);margin:6px 0 8px 0;padding:0;}
.fk-svc-card p{color:#475569;font-size:.9rem;margin:0 0 10px 0;}
.fk-svc-card ul{margin:0 0 14px 0;padding-left:18px;color:#334155;font-size:.87rem;}
.fk-svc-card li{margin-bottom:4px;}
.fk-svc-card .foot{margin-top:auto;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;}
.fk-svc-card a.go{color:var(--blue) !important;font-weight:700;font-size:.87rem;text-decoration:none;}
.fk-svc-card a.go:hover{text-decoration:underline;}
.fk-steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px;}
.fk-step{border-left:4px solid var(--blue);background:#fff;border-radius:10px;padding:16px;border-top:1px solid var(--line);border-right:1px solid var(--line);border-bottom:1px solid var(--line);}
.fk-step b{color:var(--navy);}
.fk-step p{margin:4px 0 0 0;color:#475569;font-size:.88rem;}
.fk-band{background:linear-gradient(120deg,#0F2747,#1F5FA8);border-radius:16px;padding:30px;text-align:center;margin:30px 0 6px 0;}
.fk-band h3{color:#fff;margin:0 0 8px 0;font-size:1.35rem;}
.fk-band p{color:#D6E2F0;margin:0 0 14px 0;}
.fk-band .fk-btn{margin:0 6px 6px 6px;}
.fk-info{background:#fff;border:1px solid var(--line);border-left:4px solid var(--blue);border-radius:12px;padding:14px 16px;margin-bottom:10px;word-break:break-word;color:#334155;}
.fk-info b{color:var(--navy);}
.fk-done{background:#ECFDF5;border:1px solid #A7F3D0;border-left:5px solid #059669;border-radius:12px;padding:14px 18px;margin:18px 0 0 0;color:#065F46;}
.fk-done b{color:#064E3B;}

/* ---------- footer (full width) ---------- */
.fk-foot{margin:40px -2.5rem 0 -2.5rem;background:var(--navy);color:#CBD5E1;padding:34px 2.5rem 14px 2.5rem;border-top:4px solid var(--blue);}
.fk-foot-grid{display:grid;grid-template-columns:2fr 1.2fr 1.6fr;gap:30px;}
.fk-foot h4{color:#fff;font-size:1rem;margin:0 0 10px 0;padding:0;}
.fk-foot p,.fk-foot li{font-size:.86rem;color:#CBD5E1;margin:0 0 6px 0;word-break:break-word;}
.fk-foot ul{list-style:none;padding:0;margin:0;}
.fk-foot a{color:#E2E8F0 !important;}
.fk-foot-bottom{border-top:1px solid rgba(255,255,255,.15);margin-top:20px;padding-top:12px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;font-size:.8rem;color:#94A3B8;}

/* ---------- responsive ---------- */
@media (max-width:1000px){.fk-hero-grid{grid-template-columns:1fr;}.fk-foot-grid{grid-template-columns:1fr 1fr;}}
@media (max-width:640px){
 .block-container{padding:0 .9rem !important;}
 .fk-nav,.fk-hero,.fk-foot{margin-left:-.9rem;margin-right:-.9rem;padding-left:.9rem;padding-right:.9rem;}
 .fk-hero{padding-top:36px;padding-bottom:40px;}
 .fk-hero h1{font-size:1.75rem}.fk-hero p{font-size:.97rem}
 .fk-nav-info{display:none;}
 .fk-foot-grid{grid-template-columns:1fr;}.fk-h2{font-size:1.25rem}
 .stTabs [data-baseweb="tab"]{padding:6px 10px}
}
</style>
"""


def html(s: str):
    """Render HTML; lines are stripped so Markdown never shows raw HTML."""
    st.markdown(" ".join(line.strip() for line in s.splitlines() if line.strip()), unsafe_allow_html=True)


def esc(x) -> str:
    return htmllib.escape(str(x))


def h2(title: str, sub: str = ""):
    html(f'<div class="fk-h2">{title}</div>' + (f'<p class="fk-sub">{sub}</p>' if sub else ""))


def cards(items):
    """items: list of (icon, title, text) or (icon, title, text, pill_text, pill_class)"""
    out = []
    for it in items:
        pl = f'<div style="margin-top:10px"><span class="pill {it[4]}">{it[3]}</span></div>' if len(it) > 3 else ""
        out.append(f'<div class="fk-card"><div class="ic">{it[0]}</div><h3>{it[1]}</h3><p>{it[2]}</p>{pl}</div>')
    html('<div class="fk-grid">' + "".join(out) + "</div>")


def show_df(df):
    try:
        st.dataframe(df, width="stretch", hide_index=True)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------
# 3. BUTTON LINKS
#    Buttons are links like  ?action=demo  /  ?action=talk  that reload the
#    site and open the matching pop-up form (handled in main()).
# ---------------------------------------------------------------------
def action_url(action: str, service: str = "") -> str:
    params = {"action": action}
    if service:
        params["service"] = service
    return "?" + urllib.parse.urlencode(params)


def btn(label: str, action: str, cls: str = "", service: str = "") -> str:
    return f'<a class="fk-btn {cls}" href="{esc(action_url(action, service))}" target="_self">{esc(label)}</a>'


def service_cards(include_soon: bool = True):
    out = []
    for i, s in enumerate(SERVICES, start=1):
        pts = "".join(f"<li>{esc(p)}</li>" for p in s["points"])
        if s["link"]:
            go = f'<a class="go" href="{esc(s["link"])}" target="_blank" rel="noopener">Open {esc(s["name"])} →</a>'
        else:
            go = f'<a class="go" href="{esc(action_url("demo", s["name"]))}" target="_self">Request a demo →</a>'
        out.append(f"""<div class="fk-svc-card"><div class="no">Service {i:02d}</div>
          <div style="font-size:1.9rem">{s["icon"]}</div><h3>{esc(s["name"])}</h3><p>{esc(s["text"])}</p>
          <ul>{pts}</ul><div class="foot"><span class="pill {s["cls"]}">{esc(s["status"])}</span>{go}</div></div>""")
    if include_soon:
        out.append(f"""<div class="fk-svc-card soon"><div class="no">Coming soon</div>
          <div style="font-size:1.9rem">🚀</div><h3>More services on the way</h3>
          <p>We are building new analytics and automation products for lenders. Tell us what you need.</p>
          <div class="foot"><span class="pill soon">In pipeline</span>
          <a class="go" href="{esc(action_url('talk'))}" target="_self">Suggest a service →</a></div></div>""")
    html('<div class="fk-svc">' + "".join(out) + "</div>")


# ---------------------------------------------------------------------
# 4. HEADER (nav bar + hero) + FOOTER
# ---------------------------------------------------------------------
def render_header():
    rows = "".join(f'<div class="row"><span class="dot"></span>{s["icon"]} {esc(s["name"])}</div>' for s in SERVICES)
    html(f"""
    <div class="fk-nav">
      <div class="fk-brand"><div class="fk-logo">🐪</div>
        <div><div class="fk-name">Camel <span>NBFC Analytics</span></div><div class="fk-tag">{TAGLINE}</div></div></div>
      <div class="fk-nav-right">
        <div class="fk-nav-info">✉️ <b>{esc(CONTACT_EMAIL)}</b></div>
        <div class="fk-nav-info">📍 <b>Ghatkopar West, Mumbai</b></div>
        {btn("Request a demo", "demo")}
      </div>
    </div>
    <div class="fk-hero"><div class="fk-hero-grid">
      <div>
        <span class="fk-eyebrow">Built for Indian NBFCs · MFIs · HFCs</span>
        <h1>Portfolio risk, <span>explained in minutes.</span></h1>
        <p>{BRAND} delivers ready-to-use risk analytics, daily sector risk news and rule-based credit decisioning -
        so your risk, credit and collection teams can act early with consistent, explainable numbers.</p>
        {btn("Book a free demo", "demo", "light")}
        {btn("Talk to us", "talk", "ghost")}
      </div>
      <div class="fk-hero-card"><h4>Our services</h4>{rows}
        <div class="row"><span class="dot" style="background:#94A3B8"></span>🚀 More coming soon</div>
      </div>
    </div></div>""")


def render_footer():
    svc = "".join(f"<li>{esc(s['name'])}</li>" for s in SERVICES)
    li = f'<p><a href="{LINKEDIN_URL}" target="_blank">LinkedIn</a></p>' if LINKEDIN_URL else ""
    html(f"""
    <div class="fk-foot"><div class="fk-foot-grid">
      <div><h4>🐪 {BRAND}</h4><p>Risk analytics products for Indian NBFCs, MFIs and housing-finance companies -
        consistent logic, clear dashboards and Excel-ready outputs.</p>{li}</div>
      <div><h4>Services</h4><ul>{svc}<li>More coming soon</li></ul></div>
      <div><h4>Contact</h4><p>✉️ {esc(CONTACT_EMAIL)}</p><p>📞 {esc(PHONE_TEXT)}</p>
        <p>📍 {esc(CONTACT_ADDRESS)}</p><p>🕘 {esc(WORKING_HOURS)}</p></div>
    </div>
    <div class="fk-foot-bottom"><span>© {date.today().year} {BRAND} · All rights reserved</span>
      <span>Developed by <b style="color:#fff">{DEVELOPER}</b></span></div>
    </div>""")


# ---------------------------------------------------------------------
# 5. PAGES
# ---------------------------------------------------------------------
def page_home():
    html(f"""<div class="fk-stats">
      <div class="fk-stat"><div class="n">{len(SERVICES)}</div><div class="t">services available today</div></div>
      <div class="fk-stat"><div class="n">7</div><div class="t">risk analytics modules</div></div>
      <div class="fk-stat"><div class="n">0</div><div class="t">database connections needed</div></div>
      <div class="fk-stat"><div class="n">Excel</div><div class="t">ready reports for MIS</div></div>
    </div>""")
    h2("Our services", "What we offer today - more services will be added soon.")
    service_cards(include_soon=False)
    h2("Why lenders choose us", "Built from day-to-day risk work in Indian microfinance and NBFC lending.")
    cards([
        ("⚡", "Fast answers", "Management-ready views in minutes instead of days of ad-hoc SQL and Excel work."),
        ("📐", "Consistent logic", "Same DPD buckets, vintage and roll-rate definitions every month - fewer reconciliation debates."),
        ("🔒", "Data privacy", "Upload-only design - no direct connection to your core systems or databases."),
        ("📊", "Board-ready output", "Colour heatmaps, trend charts and formatted Excel sheets for MIS packs."),
    ])
    h2("How we work")
    html("""<div class="fk-steps">
      <div class="fk-step"><b>1 · Discovery call</b><p>We understand your portfolio, products and reporting needs.</p></div>
      <div class="fk-step"><b>2 · Live demo</b><p>See the services on sample or your own anonymised data.</p></div>
      <div class="fk-step"><b>3 · Set-up</b><p>Data templates, column mapping and thresholds tuned to your policy.</p></div>
      <div class="fk-step"><b>4 · Support</b><p>Ongoing help, enhancements and new modules as you grow.</p></div>
    </div>""")
    h2("Who it is for")
    cards([
        ("🧮", "Risk & Analytics", "Vintage, roll-rate and early-mortality monitoring for portfolio reviews."),
        ("🏦", "Credit & Policy", "Spot weak cohorts, geographies and products before they reach NPA."),
        ("📞", "Collections", "Collection efficiency, forward-roll and cure-rate tracking by branch."),
        ("🛡️", "Audit & Vigilance", "Fraud early-warning screening to prioritise field verification."),
    ])
    html(f'<div class="fk-band"><h3>See it on your own portfolio</h3><p>Book a free demo - we will walk you through every service.</p>'
         f'{btn("Book a free demo", "demo", "light")}{btn("Talk to us", "talk", "ghost")}</div>')


def page_about():
    h2("About us", "Practical risk analytics, built by practitioners.")
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.markdown(
            f"**{BRAND}** started as a set of tools to answer the questions every NBFC and MFI risk team faces "
            "each month: *Which cohorts are going bad? How fast are loans rolling forward? Are new loans failing "
            "in their first few months? Is there a fraud pattern behind a sudden spike?*\n\n"
            "Instead of rebuilding the same SQL and Excel logic every month, we package proven risk methods into "
            "simple products - a Risk Analytics Studio, a daily sector risk-news service and a configurable "
            "business rule engine. Everything is designed for Indian lending - JLG, SHG, individual loans and "
            "housing finance.")
    with c2:
        html(f"""<div class="fk-card"><div class="ic">🏢</div><h3>{BRAND}</h3>
          <p>Risk analytics and data solutions for NBFC / MFI / HFC portfolios - portfolio monitoring,
          early-warning signals, rule engines and management reporting.</p>
          <p style="margin-top:10px">📍 {esc(CONTACT_ADDRESS)}</p></div>""")
    h2("Mission & vision")
    cards([
        ("🎯", "Mission", "Make good portfolio risk analytics simple, consistent and available to every lender - large or small."),
        ("🔭", "Vision", "A trusted analytics partner for inclusive lenders, turning raw loan data into early, actionable signals."),
        ("🤝", "Promise", "Transparent logic: every measure is clearly defined and explained."),
    ])
    h2("Our principles")
    cards([
        ("🧾", "Explainable", "No black boxes - definitions are shown on screen and in every report."),
        ("🔐", "Privacy first", "Upload-only design with no direct database connection."),
        ("🧩", "Modular", "Use one service or all; each works on its own."),
        ("📱", "Accessible", "Works on laptops, tablets and phones."),
    ])
    h2("Standard definitions we use")
    show_df(pd.DataFrame([
        ("DPD buckets", "0 Current · 1-30 · 31-60 · 61-90 · 91-180 · 180+"),
        ("PAR x", "POS of loans with DPD > x ÷ total POS"),
        ("Static pool", "Delinquent POS (or count) at each MOB ÷ cohort disbursement"),
        ("Roll rate", "Share of a bucket moving forward / staying / curing / closing next month"),
        ("QMA", "Loans with DPD > threshold within first N MOB (default DPD > 30, 5 MOB)"),
        ("Non-starter", "First EMI due + grace passed, zero instalments paid, DPD > 0"),
        ("Collection efficiency", "Collected against demand ÷ demand (current and overall)"),
    ], columns=["Measure", "Definition"]))


def page_products():
    h2("Products & services", f"{len(SERVICES)} services available today - more will be added soon.")
    service_cards(include_soon=True)
    h2("🧮 Risk Analytics Studio - what's inside", "Seven ready-to-use risk modules in one application.")
    cards([(ic, t, p) for ic, t, p in STUDIO_MODULES])
    h2("Outputs at a glance")
    show_df(pd.DataFrame([
        ("Static Pool", "Cohort × MOB heatmap, vintage curves", "Static pool %, cohort summary"),
        ("Roll Rate", "Transition matrix, movement mix, forward-roll trend", "Matrix value & %, bucket summary"),
        ("QMA", "QMA % by cohort (matured vs seasoning)", "Cohort summary, QMA loan list"),
        ("Non-Starter", "NS % by month, top branches / officers", "NS by dimension, loan list"),
        ("Fraud EWS", "Rule hits, risk bands, hotspots", "Flagged loans with score"),
        ("PAR & Buckets", "Bucket mix, PAR trend, geography view", "PAR by dimension, trend"),
        ("Collection Efficiency", "Demand vs collection, CE % vs target", "Monthly and branch CE"),
    ], columns=["Module", "Dashboard view", "Excel report"]))
    html(f'<div class="fk-band"><h3>Interested in any service?</h3><p>Book a demo or send us a quick message.</p>'
         f'{btn("Book a free demo", "demo", "light")}{btn("Talk to us", "talk", "ghost")}</div>')


# ---------------------------------------------------------------------
# 6. DELIVERY : E-mail + Google Sheet + local CSV  (used by all forms)
# ---------------------------------------------------------------------
def get_secret(section: str, key: str, default=""):
    """Read secrets safely (local .streamlit/secrets.toml or Streamlit Cloud Secrets)."""
    try:
        return st.secrets[section][key]
    except Exception:
        return default


def log(msg: str):
    """Printed to the PowerShell window (local) or 'Manage app > Logs' (Streamlit Cloud)."""
    print(f"[{now_ist():%Y-%m-%d %H:%M:%S} IST] {msg}", flush=True)


def save_csv(rec: dict):
    """Local CSV. Permanent on your own PC / VM; temporary on Streamlit Cloud."""
    new = pd.DataFrame([{c: rec.get(c, "") for c in ENQUIRY_COLUMNS}])
    if CONTACT_FILE.exists():
        old = pd.read_csv(CONTACT_FILE, dtype=str).fillna("")
        if list(old.columns) != ENQUIRY_COLUMNS:
            if "enquiry_type" not in old.columns:
                old["enquiry_type"] = "Contact form"
            old = old.reindex(columns=ENQUIRY_COLUMNS, fill_value="")
            pd.concat([old, new], ignore_index=True).to_csv(CONTACT_FILE, index=False)
            return
    new.to_csv(CONTACT_FILE, mode="a", index=False, header=not CONTACT_FILE.exists())


def save_google_sheet(rec: dict) -> bool:
    """Append one row to the Google Sheet via the Apps Script web-app URL in secrets [sheet]."""
    url = get_secret("sheet", "webhook_url")
    if not url:
        return False
    payload = {c: str(rec.get(c, "")) for c in ENQUIRY_COLUMNS}
    payload["token"] = get_secret("sheet", "token")
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r:
        reply = r.read().decode("utf-8", "ignore").strip()
    if reply != "ok":
        raise RuntimeError(f"Google Sheet replied: {reply[:200]}")
    return True


def send_email(subject: str, body: str, reply_to: str = "") -> bool:
    """Send via Gmail SMTP using secrets [email]. Tries port 465 (SSL), then 587 (STARTTLS)."""
    sender = get_secret("email", "sender")
    password = str(get_secret("email", "app_password")).replace(" ", "")
    receiver = get_secret("email", "receiver", NOTIFY_EMAIL)
    if not sender or not password:
        raise RuntimeError("E-mail not configured - add [email] sender and app_password in secrets.")
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{BRAND} Website <{sender}>"
    msg["To"] = receiver
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)
    ctx = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20, context=ctx) as s:
            s.login(sender, password)
            s.send_message(msg)
        return True
    except smtplib.SMTPAuthenticationError:
        raise                                   # wrong app password - port 587 will fail the same way
    except Exception as e465:
        log(f"Port 465 failed ({type(e465).__name__}: {e465}) - trying 587")
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(sender, password)
            s.send_message(msg)
        return True


def email_enquiry(rec: dict) -> bool:
    subject = f"[{rec.get('enquiry_type', 'Enquiry')}] {rec['name']} - {rec.get('interest', '')}"
    lines = [f"{c.replace('_', ' ').title()}: {rec.get(c, '')}" for c in ENQUIRY_COLUMNS if rec.get(c, "")]
    body = ("New enquiry from the Camel NBFC Analytics website\n"
            "Reply to this e-mail to answer the client directly.\n\n" + "\n".join(lines))
    return send_email(subject, body, reply_to=rec.get("email", ""))


def valid_email(x: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", x.strip()))


def submit_enquiry(rec: dict) -> bool:
    """Deliver to e-mail + Google Sheet + CSV. Succeeds if at least one channel worked."""
    rec = {k: (v.strip() if isinstance(v, str) else v) for k, v in rec.items()}
    rec["submitted_at"] = now_ist().strftime("%Y-%m-%d %H:%M:%S")
    delivered = []
    for name, fn in (("email", email_enquiry), ("google_sheet", save_google_sheet)):
        try:
            if fn(rec):
                delivered.append(name)
        except Exception as e:
            log(f"{name} FAILED: {type(e).__name__}: {e}")
    try:
        save_csv(rec)
        delivered.append("csv")
    except Exception as e:
        log(f"csv FAILED: {type(e).__name__}: {e}")
    log(f"Enquiry from {rec.get('email')} delivered to: {', '.join(delivered) or 'NOTHING'}")
    if not delivered:
        st.error(f"Sorry, we could not send your request. Please e-mail us at {CONTACT_EMAIL}.")
        return False
    return True


# ---------------------------------------------------------------------
# 7. FORMS : Book a demo  /  Talk to us  /  Contact page
# ---------------------------------------------------------------------
def demo_form(preselect: str = ""):
    st.caption("Pick a convenient date and time - we will confirm the meeting by e-mail.")
    with st.form("demo_form", clear_on_submit=False):
        a, b = st.columns(2)
        name = a.text_input("Full name *")
        email = b.text_input("Work email *")
        org = a.text_input("Organisation *")
        phone = b.text_input("Phone")
        services = st.multiselect("Services you want to see *", SERVICE_NAMES,
                                  default=[preselect] if preselect in SERVICE_NAMES else SERVICE_NAMES[:1])
        c, d = st.columns(2)
        pdate = c.date_input("Preferred date *", value=date.today() + timedelta(days=1),
                             min_value=date.today(), format="DD-MM-YYYY")
        ptime = d.selectbox("Preferred time (IST) *", DEMO_SLOTS)
        mode = st.radio("Demo mode", ["Online (Google Meet / Teams)", "In person (Mumbai)"], horizontal=True)
        msg = st.text_area("Anything we should know? (portfolio size, products, current challenges)", height=90)
        ok = st.form_submit_button("📅 Book my demo", type="primary", key="demo_submit")
    if ok:
        if not name.strip() or not org.strip() or not valid_email(email) or not services:
            st.error("Please fill name, a valid work email, organisation and at least one service.")
            return
        if submit_enquiry({"enquiry_type": "Demo booking", "name": name, "email": email, "organisation": org,
                           "phone": phone, "interest": ", ".join(services),
                           "preferred_date": pdate.strftime("%d-%m-%Y"), "preferred_time": ptime,
                           "contact_mode": mode, "message": msg}):
            st.session_state["done_msg"] = (f"<b>Demo request received.</b> Thank you, {esc(name.strip())}! "
                                            f"We will confirm your demo for {pdate:%d %b %Y}, {ptime} IST by e-mail.")
            st.success("✅ Demo request received! We will confirm the meeting by e-mail shortly.")
            st.balloons()


def talk_form():
    st.caption("Send us a quick message - we usually reply within one working day.")
    with st.form("talk_form", clear_on_submit=False):
        a, b = st.columns(2)
        name = a.text_input("Full name *")
        email = b.text_input("E-mail *")
        org = a.text_input("Organisation")
        phone = b.text_input("Phone / WhatsApp")
        topic = st.selectbox("Topic", SERVICE_NAMES + ["Pricing", "Partnership", "Custom solution", "Other"])
        mode = st.radio("How should we reach you?", ["E-mail", "Phone call", "WhatsApp"], horizontal=True)
        msg = st.text_area("Your message *", height=110)
        ok = st.form_submit_button("💬 Send message", type="primary", key="talk_submit")
    if ok:
        if not name.strip() or not msg.strip() or not valid_email(email):
            st.error("Please fill name, a valid e-mail and your message.")
            return
        if mode != "E-mail" and not phone.strip():
            st.error("Please add your phone / WhatsApp number so we can call you.")
            return
        if submit_enquiry({"enquiry_type": "Talk to us", "name": name, "email": email, "organisation": org,
                           "phone": phone, "interest": topic, "contact_mode": mode, "message": msg}):
            st.session_state["done_msg"] = (f"<b>Message received.</b> Thank you, {esc(name.strip())}! "
                                            f"We will reach you by {mode.lower()} soon.")
            st.success("✅ Message sent! We will get back to you soon.")


def open_action_popup():
    """Open the pop-up for ?action=demo / ?action=talk."""
    action = st.query_params.get("action", "")
    if action not in ("demo", "talk"):
        return
    # open on first load; afterwards re-open only when its own submit button was pressed
    # (so closing the pop-up with X does not make it re-appear on every click)
    submitted = st.session_state.get("demo_submit") or st.session_state.get("talk_submit")
    if st.session_state.get("popup_opened") and not submitted and hasattr(st, "dialog"):
        return
    st.session_state["popup_opened"] = True
    service = st.query_params.get("service", "")
    title = "📅 Book a free demo" if action == "demo" else "💬 Talk to us"
    body = (lambda: demo_form(service)) if action == "demo" else talk_form

    if hasattr(st, "dialog"):                    # Streamlit 1.37+ : real pop-up
        @st.dialog(title, width="large")
        def _popup():
            body()
        _popup()
    else:                                        # older Streamlit : show form at the top of the page
        h2(title)
        body()


def page_contact():
    h2("Contact us", "Questions, demos or a custom solution for your portfolio - we would be glad to help.")
    c1, c2 = st.columns([2, 3], gap="large")
    with c1:
        html(f"""
        <div class="fk-info">✉️ <b>Email</b><br><a href="mailto:{esc(CONTACT_EMAIL)}">{esc(CONTACT_EMAIL)}</a></div>
        <div class="fk-info">📞 <b>Phone</b><br>{esc(PHONE_TEXT)}</div>
        <div class="fk-info">📍 <b>Address</b><br>{esc(CONTACT_ADDRESS)}</div>
        <div class="fk-info">🕘 <b>Working hours</b><br>{esc(WORKING_HOURS)}</div>""")
        html(f'<div style="margin-top:6px">{btn("📅 Book a free demo", "demo")}</div>')
    with c2:
        with st.form("contact_form", clear_on_submit=True):
            a, b = st.columns(2)
            name = a.text_input("Full name *")
            email = b.text_input("Work email *")
            org = a.text_input("Organisation")
            phone = b.text_input("Phone")
            interest = st.selectbox("I am interested in", SERVICE_NAMES + ["Product demo", "Custom solution", "Other"])
            msg = st.text_area("Message *", height=130)
            sent = st.form_submit_button("Send message", type="primary")
        if sent:
            if not name.strip() or not msg.strip() or not valid_email(email):
                st.error("Please fill name, a valid email and message.")
            elif submit_enquiry({"enquiry_type": "Contact form", "name": name, "email": email, "organisation": org,
                                 "phone": phone, "interest": interest, "message": msg}):
                st.success("Thank you! Your message has been received. We will get back to you soon.")
    h2("FAQ")
    faqs = [
        ("What services do you offer today?", ", ".join(SERVICE_NAMES) + ". More services are coming soon."),
        ("Do you need access to our database?", "No. Our analytics work on uploaded CSV / Excel files."),
        ("How do I book a demo?", "Click 'Book a free demo', pick a date and time, and we will confirm by e-mail."),
        ("Can you build a custom metric or service?", "Yes - describe what you need in the form above."),
    ]
    for q, a_ in faqs:
        with st.expander(q):
            st.write(a_)


# ---------------------------------------------------------------------
# 8. ADMIN PAGE  (open the site with ?admin=1)
# ---------------------------------------------------------------------
def render_admin_inbox():
    h2("🔐 Admin")
    admin_pw = get_secret("admin", "password")
    if not admin_pw:
        st.warning("Set an admin password in secrets ([admin] password = \"...\") to use this page.")
        return
    pw = st.text_input("Admin password", type="password", key="adm_pw")
    if pw != admin_pw:
        if pw:
            st.error("Wrong password.")
        return

    # --- delivery set-up check ---
    st.subheader("Delivery set-up")
    email_ok = bool(get_secret("email", "sender") and get_secret("email", "app_password"))
    sheet_ok = bool(get_secret("sheet", "webhook_url"))
    k1, k2 = st.columns(2)
    k1.metric("E-mail", "Configured" if email_ok else "Not configured",
              get_secret("email", "receiver", NOTIFY_EMAIL) if email_ok else "add [email] secrets")
    k2.metric("Google Sheet", "Configured" if sheet_ok else "Not configured",
              "permanent record" if sheet_ok else "add [sheet] secrets")
    b1, b2 = st.columns(2)
    if b1.button("📧 Send test e-mail", key="adm_test_mail"):
        try:
            send_email(f"{BRAND} - test e-mail",
                       f"Test sent from the website admin page at {now_ist():%d-%b-%Y %H:%M} IST. E-mail delivery works.")
            st.success(f"Test e-mail sent to {get_secret('email', 'receiver', NOTIFY_EMAIL)}. Check Inbox / Spam.")
        except Exception as e:
            st.error(f"E-mail failed → {type(e).__name__}: {e}")
    if b2.button("📄 Send test row to Google Sheet", key="adm_test_sheet"):
        try:
            if save_google_sheet({"submitted_at": now_ist().strftime("%Y-%m-%d %H:%M:%S"),
                                  "enquiry_type": "TEST", "name": "Admin test", "email": NOTIFY_EMAIL}):
                st.success("Test row added to the Google Sheet.")
            else:
                st.error("Google Sheet not configured - add [sheet] webhook_url in secrets.")
        except Exception as e:
            st.error(f"Google Sheet failed → {type(e).__name__}: {e}")

    # --- local CSV view ---
    st.subheader("Enquiries saved on this server (CSV)")
    st.caption("On Streamlit Cloud this file is temporary - use the Google Sheet / e-mail as the permanent record.")
    if not CONTACT_FILE.exists():
        st.info("No enquiries in the local file yet.")
        return
    df = pd.read_csv(CONTACT_FILE, dtype=str).fillna("")
    if "enquiry_type" not in df.columns:
        df["enquiry_type"] = "Contact form"
    df = df.sort_values("submitted_at", ascending=False)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total enquiries", f"{len(df):,}")
    c2.metric("Demo bookings", f"{(df['enquiry_type'] == 'Demo booking').sum():,}")
    c3.metric("Talk to us", f"{(df['enquiry_type'] == 'Talk to us').sum():,}")
    c4.metric("Contact form", f"{(df['enquiry_type'] == 'Contact form').sum():,}")
    types = st.multiselect("Show", sorted(df["enquiry_type"].unique()), default=sorted(df["enquiry_type"].unique()))
    view = df[df["enquiry_type"].isin(types)]
    show_df(view)
    st.download_button("⬇️ Download enquiries (CSV)", view.to_csv(index=False).encode("utf-8"),
                       file_name="camel_enquiries.csv", mime="text/csv")


# ---------------------------------------------------------------------
# 9. MAIN
# ---------------------------------------------------------------------
def main():
    st.set_page_config(page_title=f"{BRAND} · {TAGLINE}", page_icon="🐪", layout="wide",
                       initial_sidebar_state="collapsed")
    st.markdown(SITE_CSS, unsafe_allow_html=True)
    render_header()
    if st.query_params.get("admin") == "1":
        render_admin_inbox()
    else:
        if st.session_state.get("done_msg"):        # confirmation shown on the page after a pop-up submit
            html(f'<div class="fk-done">✅ {st.session_state["done_msg"]}</div>')
        open_action_popup()
        tabs = st.tabs(["🏠 Home", "ℹ️ About", "🧩 Products", "✉️ Contact"])
        for tab, fn in zip(tabs, [page_home, page_about, page_products, page_contact]):
            with tab:
                fn()
    render_footer()


if __name__ == "__main__":
    main()
