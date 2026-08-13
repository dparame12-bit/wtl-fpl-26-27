
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
    border: none !important;
    font-weight: 800 !important;
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
    border-radius:18px;padding:18px 20px;color:white;
    min-height:145px; box-shadow:0 10px 25px rgba(0,0,0,.08);
}
.rivalry { background:linear-gradient(135deg,#e90052,#ff5a5f); }
.cup { background:linear-gradient(135deg,#37003c,#7a1c83); }
.prizes { background:linear-gradient(135deg,#007a5e,#00b46f); }
.chips { background:linear-gradient(135deg,#0476b8,#04b8d4); }
.feature-title {font-size:20px;font-weight:900;margin-bottom:6px;}
.feature-big {font-size:30px;font-weight:900;color:#fff;}
.small-muted {color:#ddd;font-size:12px;}
div[data-testid="stMetric"] {
    background:white;border:1px solid #ece8ef;border-radius:18px;
    padding:14px 16px;box-shadow:0 6px 18px rgba(55,0,60,.05);
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
    st.markdown('<div class="section-title">🔥 What’s coming this season</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        st.markdown("""<div class="feature-box rivalry"><div class="feature-title">🔥 Rivalry Week</div><div class="feature-big">GW10 + GW30</div><div>10 head-to-head battles each week · ₹50 per win</div></div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class="feature-box cup"><div class="feature-title">🏆 WTL Cup</div><div class="feature-big">Starts GW19</div><div>12 byes · 4 play-ins · knockout drama</div></div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""<div class="feature-box prizes"><div class="feature-title">💰 Season Prizes</div><div class="feature-big">₹40,000</div><div>League · GW · MOTM · Cup · Special Awards</div></div>""", unsafe_allow_html=True)
    with c4:
        st.markdown("""<div class="feature-box chips"><div class="feature-title">🎮 Chip Awards</div><div class="feature-big">6 prizes</div><div>BB · TC · FH across H1 and H2</div></div>""", unsafe_allow_html=True)

st.sidebar.markdown("## ⚽ WTL 26–27")
st.sidebar.caption("Fantasy. Rivalry. Chaos.")
page = st.sidebar.radio(
    "Go to",
    [
        "Dashboard","League Standings","GW Winners","Manager of the Month",
        "Rivalry Week","WTL Cup","Chip Awards","Transfer Efficiency",
        "Special Awards","Troll Awards","Rules","Prize Summary"
    ],
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
        st.markdown('<div class="section-title">📜 WTL 2026–27 Prize Rules</div>', unsafe_allow_html=True)
        st.markdown("""
### 🏆 League Finishers — ₹20,500
1st ₹7,000 · 2nd ₹5,000 · 3rd ₹3,500 · 4th ₹2,500 · 5th ₹1,500 · 6th ₹1,000

### ⚡ Gameweek Winners — ₹6,000
36 × ₹150 plus GW19 & GW38 at ₹300 each.

### 📅 Manager of the Month — ₹5,000
10 months × ₹500.

### 🏆 WTL Cup — ₹1,000
12 byes + 4 play-in fixtures, followed by knockout rounds.

### 🎮 Chip Awards — ₹1,500
BB H1/H2 · TC H1/H2 · FH H1/H2 — ₹250 each.

### ⭐ Special Awards — ₹4,000
Mid Season Champion · Biggest Climb · Transfer Tactician · Most Captain Points ·
Most Bench Points · Highest GW Without Chip · Comeback King · Mr Consistent — ₹500 each.

### 😈 Troll Awards — ₹1,000
Ctrl + Z ₹500 · Wooden Spoon ₹500.

### 🔥 Rivalry Week — ₹1,000
GW10 and GW30 · 10 randomized H2Hs each week · ₹50 per winner.

**TOTAL PRIZE POOL: ₹40,000**
""")
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
                    st.dataframe(d, use_container_width=True, hide_index=True)

    elif page == "Troll Awards":
        st.markdown('<div class="section-title">😈 Troll Awards · ₹1,000</div>', unsafe_allow_html=True)
        st.markdown("**Ctrl + Z — ₹500:** worst qualifying chip usage (TC < 6, FH < 40, BB < 8).\n\n"
                    "**Wooden Spoon — ₹500:** lowest active manager at season end, subject to activity criteria.")

    elif page == "Rules":
        st.markdown('<div class="section-title">📜 WTL 2026–27 Prize Rules</div>', unsafe_allow_html=True)
        st.markdown("""
### 🏆 League Finishers — ₹20,500
1st ₹7,000 · 2nd ₹5,000 · 3rd ₹3,500 · 4th ₹2,500 · 5th ₹1,500 · 6th ₹1,000

### ⚡ Gameweek Winners — ₹6,000
36 × ₹150 plus GW19 & GW38 at ₹300 each.

### 📅 Manager of the Month — ₹5,000
10 months × ₹500.

### 🏆 WTL Cup — ₹1,000
12 byes + 4 play-in fixtures, followed by knockout rounds.

### 🎮 Chip Awards — ₹1,500
BB H1/H2 · TC H1/H2 · FH H1/H2 — ₹250 each.

### ⭐ Special Awards — ₹4,000
Mid Season Champion · Biggest Climb · Transfer Tactician · Most Captain Points ·
Most Bench Points · Highest GW Without Chip · Comeback King · Mr Consistent — ₹500 each.

### 😈 Troll Awards — ₹1,000
Ctrl + Z ₹500 · Wooden Spoon ₹500.

### 🔥 Rivalry Week — ₹1,000
GW10 and GW30 · 10 randomized H2Hs each week · ₹50 per winner.

**TOTAL PRIZE POOL: ₹40,000**
""")

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
