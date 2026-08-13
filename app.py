
import pandas as pd
import streamlit as st
import altair as alt

from config import LEAGUE_ID, APP_TITLE, TOTAL_PRIZE_POOL, TARGET_MANAGERS
from fpl_api import get_all_league_standings, current_gw, get_manager_details
from prize_rules import (
    league_finisher_prizes, gw_winners, manager_of_month,
    transfer_efficiency, histories, special_awards, prize_summary
)
from cup_logic import cup_bracket, rivalry_draw
from utils import password_gate

st.set_page_config(page_title=APP_TITLE, page_icon="⚽", layout="wide")

FPL_CSS = """
<style>
:root {
    --purple:#37003c;
    --lime:#00ff87;
    --cyan:#04f5ff;
    --pink:#e90052;
    --ink:#171321;
    --muted:#6b7280;
}
.stApp {
    background:
      radial-gradient(circle at 88% 2%, rgba(4,245,255,.12), transparent 22%),
      radial-gradient(circle at 12% 0%, rgba(233,0,82,.08), transparent 18%),
      #f7f7fb;
}
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #37003c 0%, #220028 100%);
}
[data-testid="stSidebar"] * { color: white; }
[data-testid="stSidebar"] .stRadio label { font-weight: 600; }
[data-testid="stSidebar"] button {
    background: #00ff87 !important;
    color: #220028 !important;
    border: 2px solid #00ff87 !important;
    font-weight: 900 !important;
    box-shadow: 0 4px 14px rgba(0,255,135,.22) !important;
}
[data-testid="stSidebar"] button p,
[data-testid="stSidebar"] button span {
    color: #220028 !important;
    font-weight: 900 !important;
}
[data-testid="stSidebar"] button:hover {
    background: #ffffff !important;
    color: #37003c !important;
    border-color: #00ff87 !important;
}
[data-testid="stSidebar"] button:hover p,
[data-testid="stSidebar"] button:hover span {
    color: #37003c !important;
}
.hero {
    background: linear-gradient(120deg, #37003c 0%, #5b0a63 48%, #e90052 100%);
    border-radius: 26px;
    padding: 28px 32px;
    color: white;
    position: relative;
    overflow: hidden;
    box-shadow: 0 16px 45px rgba(55,0,60,.18);
    margin-bottom: 20px;
}
.hero:after {
    content:"⚽";
    position:absolute;
    right:30px; top:4px;
    font-size:110px;
    opacity:.12;
    transform:rotate(-12deg);
}
.hero-kicker { color:#00ff87; font-weight:900; letter-spacing:1.2px; font-size:13px; }
.hero-title { font-size:42px; line-height:1.05; font-weight:900; margin:6px 0 8px 0; }
.hero-sub { color:#f6eafa; font-size:15px; }
.card {
    background:white;
    border:1px solid #ebe7ef;
    border-radius:20px;
    padding:18px 20px;
    min-height:122px;
    box-shadow:0 8px 22px rgba(55,0,60,.06);
}
.card-label { color:#6b7280; font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.5px; }
.card-value { color:#37003c; font-size:28px; font-weight:900; margin-top:6px; }
.card-note { color:#7c7280; font-size:12px; margin-top:4px; }
.status {
    padding:14px 18px;
    border-radius:16px;
    background:linear-gradient(90deg,#effff7,#f4ffff);
    border:1px solid #b9f7dc;
    color:#174d38;
    font-weight:650;
    margin: 6px 0 22px 0;
}
.section-title {
    color:#37003c;
    font-size:25px;
    font-weight:900;
    margin:18px 0 8px 0;
}
.manager-card {
    background:white;
    border:1px solid #ece8ef;
    border-radius:16px;
    padding:14px 16px;
    height:100%;
    box-shadow:0 5px 15px rgba(55,0,60,.04);
}
.manager-num {
    width:30px;height:30px;border-radius:50%;
    background:#37003c;color:#00ff87;
    display:inline-flex;align-items:center;justify-content:center;
    font-weight:900;margin-right:8px;
}
.manager-name { font-weight:850;color:#26192a;font-size:15px; }
.team-name { color:#e90052;font-weight:700;font-size:13px;margin-top:8px; }
.entry-id { color:#8b8290;font-size:11px;margin-top:3px; }
.pending-card {
    border:2px dashed #d6cbd9;
    background:#fcf9fd;
    color:#8b8290;
    border-radius:16px;
    padding:18px;text-align:center;font-weight:800;
}
.feature-box {
    border-radius:18px;
    padding:16px 18px;
    color:white;
    min-height:205px;
    height:205px;
    box-sizing:border-box;
    box-shadow:0 10px 25px rgba(0,0,0,.08);
    display:flex;
    flex-direction:column;
    justify-content:flex-start;
    overflow:hidden;
}
.rivalry { background:linear-gradient(135deg,#e90052,#ff5a5f); }
.cup { background:linear-gradient(135deg,#37003c,#7a1c83); }
.prizes { background:linear-gradient(135deg,#007a5e,#00b46f); }
.chips { background:linear-gradient(135deg,#0476b8,#04b8d4); }
.special-feature { background:linear-gradient(135deg,#6d28d9,#a855f7); }
.feature-title {
    font-size:18px;
    line-height:1.15;
    font-weight:900;
    margin-bottom:8px;
}
.feature-big {
    font-size:25px;
    line-height:1.12;
    font-weight:900;
    color:#fff;
    margin-bottom:8px;
}
.feature-box > div:last-child {
    font-size:13px;
    line-height:1.45;
    overflow-wrap:anywhere;
}
.small-muted {color:#ddd;font-size:11px;}
div[data-testid="stMetric"] {
    background:white;border:1px solid #ece8ef;border-radius:18px;
    padding:14px 16px;box-shadow:0 6px 18px rgba(55,0,60,.05);
}

.rule-card {
    background:#ffffff;
    border:1px solid #ece8ef;
    border-left:5px solid #37003c;
    border-radius:16px;
    padding:16px 18px;
    margin:10px 0;
    box-shadow:0 5px 16px rgba(55,0,60,.05);
}
.rule-card h4 { color:#37003c; margin:0 0 6px 0; }
.rule-example {
    background:#f7f3f8;
    border-radius:14px;
    padding:13px 15px;
    margin:10px 0;
    color:#3f3342;
}
.flow {
    display:flex;
    align-items:center;
    justify-content:center;
    gap:9px;
    flex-wrap:wrap;
    margin:16px 0;
}
.flow-box {
    background:#37003c;
    color:white;
    padding:10px 14px;
    border-radius:12px;
    font-weight:800;
    text-align:center;
    min-width:115px;
}
.flow-green { background:#008a61; }
.flow-pink { background:#e90052; }
.arrow { color:#37003c; font-size:24px; font-weight:900; }
.formula {
    text-align:center;
    background:linear-gradient(90deg,#37003c,#65126e);
    color:#00ff87;
    border-radius:15px;
    padding:15px;
    margin:12px 0;
    font-size:18px;
    font-weight:900;
}

</style>
"""
st.markdown(FPL_CSS, unsafe_allow_html=True)

if not password_gate():
    st.stop()

@st.cache_data(ttl=60 * 60)
def load_managers():
    path = "data/managers.csv"
    last_error = None

    # Handles CSVs saved from GitHub/Excel/Windows in different encodings.
    for encoding in ["utf-8-sig", "utf-16", "cp1252", "latin1"]:
        try:
            df = pd.read_csv(path, encoding=encoding)
            df.columns = [str(c).strip() for c in df.columns]

            required = {"seed", "manager_name", "entry_id"}
            if required.issubset(df.columns):
                df["seed"] = pd.to_numeric(df["seed"], errors="raise").astype(int)
                df["entry_id"] = pd.to_numeric(df["entry_id"], errors="raise").astype(int)
                df["manager_name"] = df["manager_name"].astype(str).str.strip()
                return df
        except (UnicodeDecodeError, UnicodeError, pd.errors.ParserError, ValueError) as e:
            last_error = e
            continue

    raise ValueError(
        "Could not read data/managers.csv. Please save it as CSV UTF-8 with columns: "
        "seed, manager_name, entry_id."
    ) from last_error

@st.cache_data(ttl=60 * 60)
def preseason_roster():
    roster = load_managers().copy()
    rows = []
    for _, r in roster.iterrows():
        details = get_manager_details(int(r.entry_id))
        rows.append({
            "seed": int(r.seed),
            "entry_id": int(r.entry_id),
            "manager_name": r.manager_name,
            "team_name": details.get("name") or details.get("entry_name") or "Team name pending",
            "joined": True,
        })
    return pd.DataFrame(rows)

@st.cache_data(ttl=60 * 60)
def load_data():
    live = get_all_league_standings(LEAGUE_ID)
    roster = load_managers()
    if live.empty:
        return live
    live = live[live.entry_id.isin(roster.entry_id)].merge(
        roster[["entry_id","manager_name"]],
        on="entry_id", how="left", suffixes=("","_roster")
    )
    live["manager_name"] = live.manager_name_roster.fillna(live.manager_name)
    live = live.drop(columns=["manager_name_roster"])
    live = live.sort_values("total_points", ascending=False).reset_index(drop=True)
    live["current_rank"] = live.index + 1
    return live

def hero():
    st.markdown(f"""
    <div class="hero">
      <div class="hero-kicker">WTL · FANTASY PREMIER LEAGUE · 2026–27</div>
      <div class="hero-title">The race for WTL glory starts here.</div>
      <div class="hero-sub">₹40,000 on the line · 38 Gameweeks · Rivalries, cup drama, chips, awards and bragging rights.</div>
    </div>
    """, unsafe_allow_html=True)

def summary_cards(confirmed):
    cols = st.columns(4)
    cards = [
        ("Managers confirmed", f"{confirmed} / {TARGET_MANAGERS}", f"{TARGET_MANAGERS-confirmed} slots remaining"),
        ("Prize pool", f"₹{TOTAL_PRIZE_POOL:,}", "Every rupee allocated"),
        ("League code", str(LEAGUE_ID), "WTL 2026–27"),
        ("Season status", "Pre-season", "Live scoring begins with GW1"),
    ]
    for c,(label,value,note) in zip(cols,cards):
        c.markdown(f"""
        <div class="card">
          <div class="card-label">{label}</div>
          <div class="card-value">{value}</div>
          <div class="card-note">{note}</div>
        </div>
        """, unsafe_allow_html=True)

def roster_grid(roster):
    st.markdown('<div class="section-title">👥 Confirmed managers</div>', unsafe_allow_html=True)
    st.caption("Team names are pulled directly from FPL where available.")
    rows = roster.sort_values("seed").to_dict("records")
    for i in range(0, len(rows), 3):
        cols = st.columns(3)
        for col, r in zip(cols, rows[i:i+3]):
            with col:
                st.markdown(f"""
                <div class="manager-card">
                  <div><span class="manager-num">{r['seed']}</span><span class="manager-name">{r['manager_name']}</span></div>
                  <div class="team-name">⚽ {r['team_name']}</div>
                  <div class="entry-id">FPL Entry ID: {r['entry_id']}</div>
                </div>
                """, unsafe_allow_html=True)

    pending = TARGET_MANAGERS - len(rows)
    if pending > 0:
        st.write("")
        cols = st.columns(min(5, pending))
        for n, col in enumerate(cols, start=len(rows)+1):
            with col:
                st.markdown(f'<div class="pending-card">Slot {n}<br><span style="font-weight:500">Awaiting manager</span></div>', unsafe_allow_html=True)

def preseason_features():
    title_col, rules_col = st.columns([5, 1])
    with title_col:
        st.markdown('<div class="section-title">🔥 What’s coming this season</div>', unsafe_allow_html=True)
    with rules_col:
        st.write("")
        st.button(
            "📜 View Rules",
            key="home_rules_button",
            use_container_width=True,
            on_click=go_to_rules,
        )

    c1,c2,c3,c4,c5 = st.columns(5)

    with c1:
        st.markdown(
            """<div class="feature-box prizes">
            <div class="feature-title">💰 Season Prizes</div>
            <div class="feature-big">₹40,000</div>
            <div>League · GW · MOTM · Cup · Chips · Awards</div>
            </div>""",
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            """<div class="feature-box cup">
            <div class="feature-title">🏆 WTL Cup</div>
            <div class="feature-big">Starts GW19</div>
            <div>12 byes · 4 play-ins · knockout to one champion</div>
            </div>""",
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            """<div class="feature-box chips">
            <div class="feature-title">🎮 Chip Awards</div>
            <div class="feature-big">6 prizes</div>
            <div>BB · TC · FH across H1 & H2</div>
            </div>""",
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            """<div class="feature-box rivalry">
            <div class="feature-title">🔥 Rivalry Week</div>
            <div class="feature-big">GW10 + GW30</div>
            <div>Random H2H battles. Draw stays under wraps. 👀</div>
            </div>""",
            unsafe_allow_html=True,
        )

    with c5:
        st.markdown(
            """<div class="feature-box special-feature">
            <div class="feature-title">⭐ Special Awards</div>
            <div class="feature-big">8 prizes</div>
            <div>Climbs · captains · transfers · comebacks · consistency</div>
            </div>""",
            unsafe_allow_html=True,
        )


def render_rules():
    st.markdown('<div class="section-title">📜 WTL 2026–27 Rules</div>', unsafe_allow_html=True)
    st.caption("Every cash award has a fixed calculation so the tracker remains transparent throughout the season.")

    t1,t2,t3,t4,t5,t6,t7,t8 = st.tabs([
        "🏆 League",
        "⚡ GW + MOTM",
        "🏆 WTL Cup",
        "🎮 Chips",
        "⭐ Special Awards",
        "😈 Troll Awards",
        "🔥 Rivalry Week",
        "📌 Global Rules",
    ])

    with t1:
        st.markdown("### 🏆 League Finishers — ₹20,500")
        st.markdown("Final **official FPL total points after GW38** determine the league positions. Transfer-hit deductions are already reflected in the official total.")
        st.markdown("""
| Finish | Prize |
|---|---:|
| 🥇 1st | ₹7,000 |
| 🥈 2nd | ₹5,000 |
| 🥉 3rd | ₹3,500 |
| 4th | ₹2,500 |
| 5th | ₹1,500 |
| 6th | ₹1,000 |
""")
        st.markdown('<div class="rule-example"><b>Example:</b> If FPL shows 2,420 points after GW38, WTL uses 2,420. We do not add back transfer hits.</div>', unsafe_allow_html=True)

    with t2:
        st.markdown("### ⚡ Gameweek Winners — ₹6,000")
        st.markdown("The highest **official net FPL Gameweek score** wins. Transfer hits count. Normal GW prize = **₹150**; GW19 and GW38 = **₹300**.")
        st.markdown('<div class="rule-example"><b>Example:</b> 76 raw points with a -4 hit = 72 official points for the WTL GW contest.</div>', unsafe_allow_html=True)
        st.markdown("**Tie:** the GW prize is split equally.")

        st.divider()
        st.markdown("### 📅 Manager of the Month — ₹5,000")
        st.markdown("For each calendar month, we add the official net scores from all GWs assigned to that month. Highest total wins **₹500**.")
        st.markdown("""
<div class="flow">
  <div class="flow-box">GW4<br>68 pts</div><div class="arrow">+</div>
  <div class="flow-box">GW5<br>74 pts</div><div class="arrow">+</div>
  <div class="flow-box">GW6<br>61 pts</div><div class="arrow">=</div>
  <div class="flow-box flow-green">September<br>203 pts</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("**Tie:** ₹500 is split equally.")

    with t3:
        st.markdown("### 🏆 WTL Cup — ₹1,000")
        st.markdown("All 20 managers enter. **12 receive randomized R32 byes**; the remaining 8 play four opening fixtures. Each matchup is decided using the combined official net FPL score across its two-GW window.")
        st.markdown("""
<div class="flow">
  <div class="flow-box">R32<br>12 BYEs + 4 games</div><div class="arrow">→</div>
  <div class="flow-box">R16<br>16 teams</div><div class="arrow">→</div>
  <div class="flow-box">QF<br>8 teams</div><div class="arrow">→</div>
  <div class="flow-box">SF<br>4 teams</div><div class="arrow">→</div>
  <div class="flow-box flow-green">FINAL<br>2 teams</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("The draw is generated once after **20/20 managers are confirmed** and then frozen.")
        st.markdown('<div class="rule-example"><b>Example:</b> Manager A scores 61 + 70 = 131 across the two GWs. Manager B scores 67 + 60 = 127. Manager A advances.</div>', unsafe_allow_html=True)
        st.markdown("**Cup tie:** if aggregate scores are tied, higher overall WTL league position at the end of the second GW in that round advances.")

    with t4:
        st.markdown("### 🎮 Chip Awards — ₹1,500")
        st.markdown("Six prizes of **₹250**: Bench Boost H1/H2, Triple Captain H1/H2, and Free Hit H1/H2. H1 = GW1–19; H2 = GW20–38.")

        st.markdown('<div class="rule-card"><h4>Bench Boost</h4>Highest points contributed by the four bench players in that BB Gameweek.</div>', unsafe_allow_html=True)
        st.markdown('<div class="rule-example"><b>Example:</b> Bench scores 6 + 5 + 4 + 2 = <b>17 BB points</b>.</div>', unsafe_allow_html=True)

        st.markdown('<div class="rule-card"><h4>Triple Captain</h4>Measured as the <b>extra</b> points generated by TC compared with normal 2× captaincy.</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="flow">
  <div class="flow-box">Player scores<br>12</div><div class="arrow">→</div>
  <div class="flow-box">Normal captain<br>24</div><div class="arrow">→</div>
  <div class="flow-box flow-pink">Triple captain<br>36</div>
</div>
<div class="formula">TC IMPACT = 36 − 24 = +12 points</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="rule-card"><h4>Free Hit</h4>Highest official total Gameweek score in a GW where Free Hit was used.</div>', unsafe_allow_html=True)
        st.markdown("**Tie:** the relevant ₹250 chip prize is split equally.")

    with t5:
        st.markdown("### ⭐ Special Awards — ₹4,000")
        st.caption("Eight awards × ₹500.")

        st.markdown('<div class="rule-card"><h4>👑 Mid-Season Champion</h4>Manager ranked #1 on cumulative official FPL points after GW19. A tie for first splits the ₹500 prize.</div>', unsafe_allow_html=True)

        st.markdown('<div class="rule-card"><h4>📈 Biggest Climb</h4>Measures improvement in scoring output between the two halves.</div>', unsafe_allow_html=True)
        st.markdown('<div class="formula">BIGGEST CLIMB = GW20–38 POINTS − GW1–19 POINTS</div>', unsafe_allow_html=True)
        st.markdown('<div class="rule-example"><b>Example:</b> H1 = 980, H2 = 1,120 → Climb Score = <b>+140</b>. Highest score wins.</div>', unsafe_allow_html=True)

        st.markdown('<div class="rule-card"><h4>🧠 Transfer Tactician</h4>Highest genuine immediate transfer gain from ordinary transfers, after deducting transfer hits. A manager must make <b>at least 10 ordinary transfers</b> during the season to qualify. Wildcard and Free Hit transfers are excluded from both the calculation and the 10-transfer minimum.</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="flow">
  <div class="flow-box">Player OUT<br>2 pts</div><div class="arrow">→</div>
  <div class="flow-box flow-green">Player IN<br>11 pts</div><div class="arrow">=</div>
  <div class="flow-box">Transfer gain<br>+9</div><div class="arrow">−</div>
  <div class="flow-box flow-pink">Hit<br>4</div><div class="arrow">=</div>
  <div class="flow-box flow-green">Net gain<br>+5</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("For every normal transfer, the app compares **incoming player's points vs outgoing player's points in that same GW**. These gains are summed across the season and official hit costs are deducted once per GW. Managers with fewer than **10 qualifying ordinary transfers** are shown for transparency but cannot win the award.")
        st.markdown('<div class="formula">NET TRANSFER POINTS = Σ(IN POINTS − OUT POINTS) − TRANSFER HIT COST</div>', unsafe_allow_html=True)

        st.markdown('<div class="rule-card"><h4>©️ Most Captain Points</h4>Highest cumulative normal captain contribution across the season. Each captain is counted at 2×. On TC weeks, we still use 2× here so the extra TC point is rewarded only in the Chip Award.</div>', unsafe_allow_html=True)

        st.markdown('<div class="rule-card"><h4>🪑 Most Bench Points</h4>Highest cumulative points genuinely left unused on the bench. Bench Boost GWs are excluded.</div>', unsafe_allow_html=True)

        st.markdown('<div class="rule-card"><h4>🚀 Highest GW Without Chip</h4>Highest official net GW score achieved without Wildcard, Free Hit, Triple Captain or Bench Boost.</div>', unsafe_allow_html=True)

        st.markdown('<div class="rule-card"><h4>🔄 Comeback King</h4>Biggest improvement in actual WTL league position from GW19 to GW38.</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="flow">
  <div class="flow-box">GW19 Rank<br>16th</div><div class="arrow">→</div>
  <div class="flow-box flow-green">GW38 Rank<br>5th</div><div class="arrow">=</div>
  <div class="flow-box flow-green">+11 places</div>
</div>
""", unsafe_allow_html=True)

        st.markdown('<div class="rule-card"><h4>🎯 Mr Consistent</h4>Among managers finishing in the overall Top 10, the lowest standard deviation of weekly GW rank wins. This rewards consistently strong weekly performance rather than a few huge spikes.</div>', unsafe_allow_html=True)

    with t6:
        st.markdown("### 😈 Troll Awards — ₹1,000")
        st.markdown("Two awards of **₹500**.")

        st.markdown('<div class="rule-card"><h4>🤦 Ctrl + Z</h4>The worst qualifying chip usage. A chip enters contention if TC impact &lt; 6, FH total &lt; 40, or BB impact &lt; 8.</div>', unsafe_allow_html=True)
        st.markdown("""
<div class="flow">
  <div class="flow-box">TC impact<br>+4</div><div class="arrow">✓</div>
  <div class="flow-box">FH score<br>58</div><div class="arrow">✗</div>
  <div class="flow-box">BB impact<br>6</div><div class="arrow">✓</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("Among all qualifying disasters, the **lowest impact** wins Ctrl + Z. 😂")

        st.markdown('<div class="rule-card"><h4>🥄 Wooden Spoon</h4>Lowest final overall FPL points among active managers.</div>', unsafe_allow_html=True)
        st.markdown("To qualify, a manager must have made a transfer and/or played a chip in at least **25 different GWs**. If the bottom manager ghosted early, the award moves to the next-lowest eligible manager.")

    with t7:
        st.markdown("### 🔥 WTL Rivalry Week — ₹1,000")
        st.markdown("Two special H2H events: **GW10 and GW30**. Before each event, the 20 managers are randomly paired into 10 fixtures.")
        st.markdown("""
<div class="flow">
  <div class="flow-box">Manager A<br>78 pts</div>
  <div class="arrow">VS</div>
  <div class="flow-box">Manager B<br>69 pts</div>
  <div class="arrow">→</div>
  <div class="flow-box flow-green">Manager A<br>₹50</div>
</div>
""", unsafe_allow_html=True)
        st.markdown("Official **net** GW score is used, so transfer hits count. Each matchup winner receives **₹50**.")
        st.markdown("10 winners × ₹50 × 2 Rivalry Weeks = **₹1,000**.")
        st.markdown("**Tie:** ₹50 is split ₹25 / ₹25.")
        st.markdown("Rivalry Week is completely independent of the league table and WTL Cup.")

    with t8:
        st.markdown("### 📌 Global Rules")
        st.markdown("""
- **Official FPL data is the source of truth.**
- Wherever we say **official/net GW score**, transfer-hit deductions count.
- Cash prizes tied on the defined winning metric are **split equally**, unless a specific tiebreak is stated.
- WTL Cup and Rivalry Week draws are randomized once and then **frozen**.
- If FPL retrospectively adjusts points, WTL calculations update with the corrected FPL data.
- Special-award leaderboards shown during the season are **live/provisional** until the relevant award can be finalized.
- Wildcard and Free Hit GWs are excluded from **Transfer Tactician** because those transfer sets are unlimited or temporary.
- **Transfer Tactician eligibility:** minimum 10 ordinary transfers across the season. Managers below the threshold remain visible but are marked ineligible.
""")
        st.success("Total season allocation: ₹40,000 ✅")


def go_to_rules():
    st.session_state["page_nav"] = "Rules"

if "page_nav" not in st.session_state:
    st.session_state["page_nav"] = "Dashboard"

st.sidebar.markdown("## ⚽ WTL 26–27")
st.sidebar.caption("Fantasy. Rivalry. Chaos.")
page = st.sidebar.radio(
    "Go to",
    [
        "Dashboard","League Standings","GW Winners","Manager of the Month",
        "Rivalry Week","WTL Cup","Chip Awards","Transfer Efficiency",
        "Special Awards","Troll Awards","Rules","Prize Summary"
    ],
    key="page_nav",
)
if st.sidebar.button("🔄 Refresh FPL data"):
    st.cache_data.clear()
    st.rerun()

standings = load_data()
roster = preseason_roster()
confirmed = len(roster)
gw = current_gw()

hero()

if page == "Dashboard":
    summary_cards(confirmed)

    if standings.empty:
        st.markdown(
            '<div class="status">🟢 <b>Pre-season mode:</b> FPL is not publishing league standings yet. '
            'The tracker is live and will switch automatically to full scoring mode once standings become available.</div>',
            unsafe_allow_html=True,
        )
        preseason_features()
        roster_grid(roster)
    else:
        st.markdown(
            f'<div class="status">🟢 Live scoring mode · Standings updated through GW{gw}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="section-title">🏁 Ranking Race</div>', unsafe_allow_html=True)
        h = histories(standings)
        if not h.empty:
            h["rank"] = h.groupby("GW").cumulative_points.rank(method="min", ascending=False)
            chart = (
                alt.Chart(h)
                .mark_line(point=True, strokeWidth=3)
                .encode(
                    x=alt.X("GW:Q", scale=alt.Scale(domain=[1,38]), title="Gameweek"),
                    y=alt.Y("rank:Q", scale=alt.Scale(reverse=True), title="League Rank"),
                    color=alt.Color("team_name:N", scale=alt.Scale(scheme="category20"), title="Team"),
                    tooltip=["GW","team_name","manager_name","cumulative_points","rank"],
                )
                .properties(height=520)
                .interactive()
            )
            st.altair_chart(chart, use_container_width=True)

        st.markdown('<div class="section-title">📊 Current Standings</div>', unsafe_allow_html=True)
        st.dataframe(
            standings[["current_rank","team_name","manager_name","total_points","gw_points"]],
            use_container_width=True, hide_index=True
        )

elif standings.empty:
    summary_cards(confirmed)
    st.markdown(
        '<div class="status">🔒 This section unlocks automatically once FPL begins publishing 2026–27 gameweek data.</div>',
        unsafe_allow_html=True,
    )
    if page == "Rivalry Week":
        st.markdown('<div class="section-title">🔥 Rivalry Week</div>', unsafe_allow_html=True)
        st.info(f"Draw locked at {confirmed}/{TARGET_MANAGERS} managers. It will be generated once all 20 are confirmed.")
        st.markdown("**Scheduled:** GW10 and GW30 · 10 H2H fixtures · ₹50 to each winner.")
    elif page == "WTL Cup":
        st.markdown('<div class="section-title">🏆 WTL Cup</div>', unsafe_allow_html=True)
        st.info(f"Draw locked at {confirmed}/{TARGET_MANAGERS} managers. It will be generated once all 20 are confirmed.")
        st.markdown("**Format:** 12 first-round byes + 4 play-in fixtures → knockout rounds → one champion.")
    elif page == "Rules":
        render_rules()
    elif page == "Prize Summary":
        st.markdown('<div class="section-title">💰 Prize Summary</div>', unsafe_allow_html=True)
        st.info("Prize payouts will begin populating after GW1. Total season allocation is ₹40,000.")
    else:
        st.info("Live leaderboard data for this section will appear after GW1.")

else:
    if page == "League Standings":
        st.markdown(f'<div class="section-title">🏆 League Standings · GW{gw}</div>', unsafe_allow_html=True)
        st.dataframe(league_finisher_prizes(standings), use_container_width=True, hide_index=True)

    elif page == "GW Winners":
        st.markdown('<div class="section-title">⚡ Gameweek Winners</div>', unsafe_allow_html=True)
        d = gw_winners(standings)
        if not d.empty:
            chart = alt.Chart(d).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                x=alt.X("GW:O", title="Gameweek"),
                y=alt.Y("points:Q", title="Winning Score"),
                color=alt.Color("team_name:N", scale=alt.Scale(scheme="tableau20"), legend=None),
                tooltip=list(d.columns),
            ).properties(height=340)
            st.altair_chart(chart, use_container_width=True)
            st.dataframe(d, use_container_width=True, hide_index=True)

    elif page == "Manager of the Month":
        st.markdown('<div class="section-title">📅 Manager of the Month</div>', unsafe_allow_html=True)
        st.dataframe(manager_of_month(standings), use_container_width=True, hide_index=True)

    elif page == "Rivalry Week":
        st.markdown('<div class="section-title">🔥 WTL Rivalry Week</div>', unsafe_allow_html=True)
        d,note = rivalry_draw(standings)
        st.info(note)
        if not d.empty: st.dataframe(d, use_container_width=True, hide_index=True)

    elif page == "WTL Cup":
        st.markdown('<div class="section-title">🏆 WTL Cup</div>', unsafe_allow_html=True)
        d,note = cup_bracket(standings)
        st.info(note)
        if not d.empty: st.dataframe(d, use_container_width=True, hide_index=True)

    elif page == "Chip Awards":
        st.markdown('<div class="section-title">🎮 Chip Awards</div>', unsafe_allow_html=True)
        st.info("BB, TC and FH each have H1 and H2 prizes worth ₹250.")

    elif page == "Transfer Efficiency":
        st.markdown('<div class="section-title">📈 Transfer Efficiency</div>', unsafe_allow_html=True)
        d = transfer_efficiency(standings)
        st.caption("(Total points − penalty points) / (38 + number of hits)")
        if not d.empty:
            st.altair_chart(
                alt.Chart(d).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
                    x="transfer_efficiency:Q",
                    y=alt.Y("team_name:N", sort="-x"),
                    color=alt.Color("team_name:N", scale=alt.Scale(scheme="category20"), legend=None),
                    tooltip=list(d.columns),
                ).properties(height=500),
                use_container_width=True,
            )
            st.dataframe(d, use_container_width=True, hide_index=True)

    elif page == "Special Awards":
        st.markdown('<div class="section-title">⭐ Special Awards · ₹4,000</div>', unsafe_allow_html=True)
        awards = special_awards(standings)
        tabs = st.tabs([
            "Mid Season","Biggest Climb","Transfer Tactician","Captain Points",
            "Bench Points","Highest GW No Chip","Comeback King","Mr Consistent"
        ])
        keys = [
            "Mid Season Champion","Biggest Climb","Transfer Tactician","Most Captain Points",
            "Most Bench Points","Highest GW Without Chip","Comeback King","Mr Consistent"
        ]
        for tab,key in zip(tabs,keys):
            with tab:
                d = awards.get(key, pd.DataFrame())
                st.markdown(f"### {key}")
                if d.empty:
                    st.info("No data available yet.")
                else:
                    st.metric("Current Leader", d.iloc[0].team_name)
                    if key == "Transfer Tactician":
                        st.caption(
                            "Net Transfer Gain = Σ(incoming GW points − outgoing GW points) − transfer-hit cost. "
                            "Minimum 10 ordinary transfers to qualify; Wildcard/Free Hit transfers are excluded."
                        )
                        eligible_d = d[d["eligible"] == "Yes"].copy()
                        if eligible_d.empty:
                            st.info("No manager has reached the 10 ordinary-transfer eligibility threshold yet.")
                        else:
                            leader = eligible_d.iloc[0]
                            st.metric("Current Eligible Leader", leader.team_name)
                            chart = (
                                alt.Chart(eligible_d.head(15))
                                .mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5)
                                .encode(
                                    x=alt.X("net_transfer_gain:Q", title="Net Transfer Gain"),
                                    y=alt.Y("team_name:N", sort="-x", title="Team"),
                                    color=alt.Color("net_transfer_gain:Q", scale=alt.Scale(scheme="greens"), legend=None),
                                    tooltip=[
                                        "team_name","manager_name","ordinary_transfers",
                                        "gross_transfer_gain","hit_cost","net_transfer_gain","eligible"
                                    ],
                                )
                                .properties(height=430)
                            )
                            st.altair_chart(chart, use_container_width=True)

                        display_cols = [
                            "team_name","manager_name","ordinary_transfers",
                            "gross_transfer_gain","hit_cost","net_transfer_gain","eligible"
                        ]
                        display = d[display_cols].rename(columns={
                            "team_name": "Team",
                            "manager_name": "Manager",
                            "ordinary_transfers": "Ordinary Transfers",
                            "gross_transfer_gain": "Gross Transfer Gain",
                            "hit_cost": "Hit Cost",
                            "net_transfer_gain": "Net Transfer Gain",
                            "eligible": "Eligible?",
                        })
                        st.dataframe(display, use_container_width=True, hide_index=True)
                    else:
                        st.dataframe(d, use_container_width=True, hide_index=True)

    elif page == "Troll Awards":
        st.markdown('<div class="section-title">😈 Troll Awards · ₹1,000</div>', unsafe_allow_html=True)
        st.markdown("**Ctrl + Z — ₹500:** worst qualifying chip usage (TC < 6, FH < 40, BB < 8).\n\n"
                    "**Wooden Spoon — ₹500:** lowest active manager at season end, subject to activity criteria.")

    elif page == "Rules":
        render_rules()
    elif page == "Prize Summary":
        rd,_ = rivalry_draw(standings)
        d = prize_summary(standings, rd)
        st.markdown('<div class="section-title">💰 Prize Summary</div>', unsafe_allow_html=True)
        st.caption("Live/projected prize view. Green cells indicate a current prize allocation.")
        prize_cols = d.columns[5:]
        def hi(v):
            try:
                return "background-color:#dcfce7;font-weight:700;color:#166534" if float(v)>0 else ""
            except Exception:
                return ""
        st.dataframe(
            d.style.map(hi, subset=prize_cols).format({c:"₹{:,.0f}" for c in prize_cols}),
            use_container_width=True, hide_index=True
        )
        st.metric("Current Allocated / Projected", f"₹{d['Total Prize'].sum():,.0f}")
