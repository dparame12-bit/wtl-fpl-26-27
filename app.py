import os
import pandas as pd
import streamlit as st
import altair as alt
from config import LEAGUE_ID, APP_TITLE, TOTAL_PRIZE_POOL, TARGET_MANAGERS, PRIZES
from fpl_api import get_all_league_standings, current_gw
from prize_rules import league_finisher_prizes, gw_winners, manager_of_month, transfer_efficiency, histories, special_awards, prize_summary
from cup_logic import cup_bracket, rivalry_draw
from utils import password_gate

st.set_page_config(page_title=APP_TITLE,page_icon='⚽',layout='wide')
if not password_gate(): st.stop()

@st.cache_data(ttl=60*60)
def load_managers(): return pd.read_csv('data/managers.csv')

@st.cache_data(ttl=60*60)
def load_data():
    live=get_all_league_standings(LEAGUE_ID)
    roster=load_managers()
    if live.empty: return live
    # Keep only confirmed WTL entrants and use canonical manager spelling from roster.
    live=live[live.entry_id.isin(roster.entry_id)].merge(roster[['entry_id','manager_name']],on='entry_id',how='left',suffixes=('','_roster'))
    live['manager_name']=live.manager_name_roster.fillna(live.manager_name); live=live.drop(columns=['manager_name_roster'])
    live=live.sort_values('total_points',ascending=False).reset_index(drop=True); live['current_rank']=live.index+1
    return live

st.sidebar.title('⚽ WTL 26–27')
page=st.sidebar.radio('Go to',['Dashboard','League Standings','GW Winners','Manager of the Month','Rivalry Week','WTL Cup','Chip Awards','Transfer Efficiency','Special Awards','Troll Awards','Rules','Prize Summary'])
if st.sidebar.button('🔄 Refresh FPL data'):
    st.cache_data.clear(); st.rerun()

standings=load_data(); gw=current_gw()
st.title(APP_TITLE)
if standings.empty:
    st.warning('The FPL league is not returning standings yet. The app is ready and will populate automatically once FPL exposes league data.'); st.stop()

if page=='Dashboard':
    c1,c2,c3,c4=st.columns(4); c1.metric('Current GW',gw); c2.metric('Confirmed Managers',f"{len(standings)} / {TARGET_MANAGERS}"); c3.metric('Prize Pool',f"₹{TOTAL_PRIZE_POOL:,}"); c4.metric('League Code',LEAGUE_ID)
    if len(standings)<TARGET_MANAGERS: st.info(f"{TARGET_MANAGERS-len(standings)} spots still pending. Cup and Rivalry Week draws stay locked until all 20 are in.")
    st.subheader('🏁 Live Race')
    h=histories(standings)
    if not h.empty:
        h['rank']=h.groupby('GW').cumulative_points.rank(method='min',ascending=False)
        chart=alt.Chart(h).mark_line(point=True).encode(x=alt.X('GW:Q',scale=alt.Scale(domain=[1,38])),y=alt.Y('rank:Q',sort='ascending',scale=alt.Scale(reverse=True),title='League Rank'),color=alt.Color('team_name:N',legend=alt.Legend(title='Team')),tooltip=['GW','team_name','manager_name','cumulative_points','rank']).properties(height=520)
        st.altair_chart(chart,use_container_width=True)
    st.subheader('Current Standings'); st.dataframe(standings[['current_rank','team_name','manager_name','total_points','gw_points']],use_container_width=True,hide_index=True)

elif page=='League Standings':
    st.caption(f'As of GW{gw}'); st.dataframe(league_finisher_prizes(standings),use_container_width=True,hide_index=True)
elif page=='GW Winners':
    st.info('₹150 per GW; GW19 and GW38 are ₹300 bonus gameweeks.'); st.dataframe(gw_winners(standings),use_container_width=True,hide_index=True)
elif page=='Manager of the Month':
    st.dataframe(manager_of_month(standings),use_container_width=True,hide_index=True)
elif page=='Rivalry Week':
    st.subheader('🔥 WTL Rivalry Week'); d,note=rivalry_draw(standings); st.info(note)
    if not d.empty: st.dataframe(d,use_container_width=True,hide_index=True)
elif page=='WTL Cup':
    st.subheader('🏆 WTL Cup'); d,note=cup_bracket(standings); st.info(note)
    if not d.empty: st.dataframe(d,use_container_width=True,hide_index=True)
elif page=='Chip Awards':
    st.subheader('🎮 Chip Awards'); st.info('Live chip leaderboards activate as chips are used. BB, TC and FH each have H1 and H2 prizes of ₹250.')
elif page=='Transfer Efficiency':
    d=transfer_efficiency(standings); st.caption('(Total points − penalty points) / (38 + number of hits)')
    if not d.empty:
        st.altair_chart(alt.Chart(d).mark_bar().encode(x='transfer_efficiency:Q',y=alt.Y('team_name:N',sort='-x'),color='team_name:N',tooltip=list(d.columns)).properties(height=500),use_container_width=True); st.dataframe(d,use_container_width=True,hide_index=True)
elif page=='Special Awards':
    st.subheader('⭐ Special Awards — ₹4,000'); awards=special_awards(standings)
    tabs=st.tabs(['Mid Season','Biggest Climb','Transfer Tactician','Captain Points','Bench Points','Highest GW No Chip','Comeback King','Mr Consistent'])
    keys=['Mid Season Champion','Biggest Climb','Transfer Tactician','Most Captain Points','Most Bench Points','Highest GW Without Chip','Comeback King','Mr Consistent']
    for tab,key in zip(tabs,keys):
        with tab:
            d=awards.get(key,pd.DataFrame()); st.markdown(f'### {key}')
            if d.empty: st.info('No data available yet.')
            else:
                st.metric('Current Leader',d.iloc[0].team_name); st.dataframe(d,use_container_width=True,hide_index=True)
elif page=='Troll Awards':
    st.subheader('😈 Troll Awards — ₹1,000'); st.markdown('**Ctrl + Z — ₹500:** worst qualifying chip usage (TC < 6, FH < 40, BB < 8).\n\n**Wooden Spoon — ₹500:** lowest active manager at season end (minimum 25 active GWs; otherwise next-lowest active manager).')
elif page=='Rules':
    st.subheader('📜 WTL 2026–27 Prize Rules')
    st.markdown('''
### 🏆 League Finishers — ₹20,500
1st ₹7,000 · 2nd ₹5,000 · 3rd ₹3,500 · 4th ₹2,500 · 5th ₹1,500 · 6th ₹1,000

### ⚡ Gameweek Winners — ₹6,000
36 × ₹150 plus GW19 & GW38 at ₹300 each.

### 📅 Manager of the Month — ₹5,000
10 months × ₹500.

### 🏆 WTL Cup — ₹1,000
20 managers; 12 receive first-round byes and 8 play four play-in ties. Every tie spans two GWs.

### 🎮 Chip Awards — ₹1,500
Best Bench Boost, Triple Captain and Free Hit in H1 and H2 — ₹250 each.

### ⭐ Special Awards — ₹4,000
Mid Season Champion, Biggest Climb, Transfer Tactician, Most Captain Points, Most Bench Points, Highest GW Without Chip, Comeback King and Mr Consistent — ₹500 each.

### 😈 Troll Awards — ₹1,000
Ctrl + Z ₹500 · Wooden Spoon ₹500.

### 🔥 WTL Rivalry Week — ₹1,000
GW10 and GW30. Ten randomized H2H fixtures each week; ₹50 per fixture.

**Total: ₹40,000**
''')
elif page=='Prize Summary':
    rd,_=rivalry_draw(standings); d=prize_summary(standings,rd); st.subheader('💰 Prize Summary'); st.caption('Live/projected prize view. Green cells indicate a current prize allocation.')
    prize_cols=d.columns[5:]
    def hi(v):
        try:return 'background-color:#dcfce7;font-weight:700' if float(v)>0 else ''
        except:return ''
    st.dataframe(d.style.map(hi,subset=prize_cols).format({c:'₹{:,.0f}' for c in prize_cols}),use_container_width=True,hide_index=True)
    st.metric('Current Allocated / Projected',f"₹{d['Total Prize'].sum():,.0f}")
