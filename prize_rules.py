import pandas as pd
import numpy as np
from config import PRIZES, MONTH_GW_MAP
from fpl_api import get_manager_history, get_manager_picks, current_gw

def histories(standings):
    rows=[]
    for _,r in standings.iterrows():
        h=get_manager_history(int(r.entry_id)).get('current',[])
        cum=0
        for x in h:
            cum += int(x.get('points',0))
            rows.append({'entry_id':int(r.entry_id),'team_name':r.team_name,'manager_name':r.manager_name,'GW':int(x['event']),'points':int(x.get('points',0)),'cumulative_points':cum,'bench_points':int(x.get('points_on_bench',0)),'transfer_cost':int(x.get('event_transfers_cost',0)),'transfers':int(x.get('event_transfers',0))})
    return pd.DataFrame(rows)

def league_finisher_prizes(s):
    d=s.copy(); d['Projected Prize']=d.current_rank.map(PRIZES['league_finishers']).fillna(0).astype(int); return d

def gw_winners(s):
    d=histories(s)
    if d.empty:return d
    w=d.sort_values(['GW','points'],ascending=[True,False]).groupby('GW',as_index=False).head(1).copy()
    w['prize']=w.GW.map(lambda g:PRIZES['gw_bonus'].get(int(g),PRIZES['gw_normal']))
    return w[['GW','team_name','manager_name','points','prize','entry_id']]

def manager_of_month(s):
    d=histories(s); rows=[]
    if d.empty:return d
    for month,gws in MONTH_GW_MAP.items():
        x=d[d.GW.isin(gws)].groupby(['entry_id','team_name','manager_name'],as_index=False).points.sum()
        if not x.empty:
            top=x.points.max(); winners=x[x.points==top].copy(); winners['month']=month; winners['prize']=PRIZES['manager_of_month']/len(winners); rows.append(winners)
    return pd.concat(rows,ignore_index=True)[['month','team_name','manager_name','points','prize','entry_id']] if rows else pd.DataFrame()

def transfer_efficiency(s):
    d=histories(s); rows=[]
    for eid,g in d.groupby('entry_id'):
        penalty=g.transfer_cost.abs().sum(); hits=int(penalty//4); total=g.points.sum();
        r=g.iloc[0]; rows.append({'entry_id':eid,'team_name':r.team_name,'manager_name':r.manager_name,'total_points':total,'penalty_points':penalty,'hits':hits,'transfer_efficiency':round((total-penalty)/(38+hits),2)})
    return pd.DataFrame(rows).sort_values('transfer_efficiency',ascending=False) if rows else pd.DataFrame()

def special_awards(s):
    d=histories(s); out={}
    if d.empty:return out
    # mid season
    m=d[d.GW<=19].groupby(['entry_id','team_name','manager_name'],as_index=False).points.sum().sort_values('points',ascending=False); out['Mid Season Champion']=m
    bench=d.groupby(['entry_id','team_name','manager_name'],as_index=False).bench_points.sum().sort_values('bench_points',ascending=False); out['Most Bench Points']=bench
    h1=d[d.GW<=19].groupby('entry_id').points.sum(); h2=d[d.GW>=20].groupby('entry_id').points.sum(); base=s[['entry_id','team_name','manager_name']].copy(); base['h1']=base.entry_id.map(h1).fillna(0); base['h2']=base.entry_id.map(h2).fillna(0); base['climb_score']=base.h2-base.h1; out['Biggest Climb']=base.sort_values('climb_score',ascending=False)
    # captain points via picks
    caps=[]; no_chip=[]
    for _,r in s.iterrows():
        hist=get_manager_history(int(r.entry_id)); chips={int(c['event']) for c in hist.get('chips',[])}
        cap_total=0
        for h in hist.get('current',[]):
            gw=int(h['event'])
            if gw not in chips:no_chip.append({'entry_id':r.entry_id,'team_name':r.team_name,'manager_name':r.manager_name,'GW':gw,'points':int(h.get('points',0))})
            try:
                p=get_manager_picks(int(r.entry_id),gw)
                for pick in p.get('picks',[]):
                    if pick.get('is_captain'):
                        # FPL picks endpoint does not expose player event points directly; use entry_history captain-independent fallback omitted.
                        pass
            except Exception: pass
        caps.append({'entry_id':r.entry_id,'team_name':r.team_name,'manager_name':r.manager_name,'captain_points':cap_total})
    out['Most Captain Points']=pd.DataFrame(caps).sort_values('captain_points',ascending=False)
    out['Highest GW Without Chip']=pd.DataFrame(no_chip).sort_values('points',ascending=False).groupby('entry_id',as_index=False).head(1).sort_values('points',ascending=False) if no_chip else pd.DataFrame()
    # comeback: GW19 rank vs current rank, based on cumulative points
    if not m.empty:
        mr=m.sort_values('points',ascending=False).reset_index(drop=True); mr['gw19_rank']=mr.index+1
        cb=s[['entry_id','team_name','manager_name','current_rank']].merge(mr[['entry_id','gw19_rank']],on='entry_id',how='left'); cb['places_gained']=cb.gw19_rank-cb.current_rank; out['Comeback King']=cb.sort_values('places_gained',ascending=False)
    # consistency: lowest SD of weekly rank, top-10 current only
    ranks=[]
    for gw,x in d.groupby('GW'):
        x=x.copy(); x['gw_rank']=x['points'].rank(method='min',ascending=False); ranks.append(x[['entry_id','gw_rank']])
    rr=pd.concat(ranks) if ranks else pd.DataFrame(); cons=rr.groupby('entry_id').gw_rank.std().reset_index(name='rank_volatility').merge(s[['entry_id','team_name','manager_name','current_rank']],on='entry_id'); cons=cons[cons.current_rank<=10].sort_values('rank_volatility'); out['Mr Consistent']=cons
    te=transfer_efficiency(s); out['Transfer Efficiency']=te
    # Transfer Tactician proxy: points scored on GWs where transfers made, less hits
    tt=d[d.transfers>0].groupby(['entry_id','team_name','manager_name'],as_index=False).agg(gross_points=('points','sum'),hits_cost=('transfer_cost','sum'),transfer_count=('transfers','sum')); tt['net_transfer_points']=tt.gross_points-tt.hits_cost.abs(); out['Transfer Tactician']=tt.sort_values('net_transfer_points',ascending=False)
    return out

def prize_summary(s, rivalry=None):
    b=s[['entry_id','team_name','manager_name','current_rank','total_points']].copy(); b['League Finish']=b.current_rank.map(PRIZES['league_finishers']).fillna(0)
    for col in ['GW Winners','Manager of Month','WTL Cup','Chip Awards','Mid Season','Biggest Climb','Transfer Tactician','Captain Points','Bench Points','Highest GW No Chip','Comeback King','Mr Consistent','Ctrl + Z','Wooden Spoon','Rivalry Week']: b[col]=0.0
    gw=gw_winners(s)
    if not gw.empty:
        sums=gw.groupby('entry_id').prize.sum(); b['GW Winners']=b.entry_id.map(sums).fillna(0)
    mom=manager_of_month(s)
    if not mom.empty:
        sums=mom.groupby('entry_id').prize.sum(); b['Manager of Month']=b.entry_id.map(sums).fillna(0)
    awards=special_awards(s)
    mapping={'Mid Season Champion':('Mid Season',500),'Biggest Climb':('Biggest Climb',500),'Transfer Tactician':('Transfer Tactician',500),'Most Captain Points':('Captain Points',500),'Most Bench Points':('Bench Points',500),'Highest GW Without Chip':('Highest GW No Chip',500),'Comeback King':('Comeback King',500),'Mr Consistent':('Mr Consistent',500)}
    for key,(col,amt) in mapping.items():
        x=awards.get(key,pd.DataFrame())
        if not x.empty:
            metric=[c for c in x.columns if c not in ['entry_id','team_name','manager_name','current_rank','GW','h1','h2']][-1]
            top=x.iloc[0][metric]; tied=x[x[metric]==top]; each=amt/len(tied)
            b.loc[b.entry_id.isin(tied.entry_id),col]=each
    # Wooden spoon live projection; eligibility enforced at season end.
    if not s.empty:b.loc[b.entry_id==s.sort_values('total_points').iloc[0].entry_id,'Wooden Spoon']=500
    if rivalry is not None and not rivalry.empty:
        for _,r in rivalry.iterrows():
            if r.Winner!='Tie':
                eid=s.loc[s.team_name==r.Winner,'entry_id'];
                if not eid.empty:b.loc[b.entry_id==eid.iloc[0],'Rivalry Week'] += float(r.Prize)
    prize_cols=b.columns[5:]; b['Total Prize']=b[prize_cols].sum(axis=1); return b.sort_values(['Total Prize','total_points'],ascending=[False,False])
