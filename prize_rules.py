import pandas as pd
import numpy as np
from config import PRIZES, MONTH_GW_MAP
from fpl_api import get_manager_history, get_manager_picks, get_manager_transfers, get_event_live, current_gw


def _event_points_map(gw: int):
    live = get_event_live(int(gw))
    return {
        int(e["id"]): int(e.get("stats", {}).get("total_points", 0))
        for e in live.get("elements", [])
    }

def _chip_map(entry_id: int):
    hist = get_manager_history(int(entry_id))
    return {
        int(c.get("event", 0)): c.get("name")
        for c in hist.get("chips", [])
    }

def transfer_tactician_table(s):
    """
    Transfer Tactician:
    For each permanent transfer, measure immediate-GW gain:
        incoming player GW points - outgoing player GW points.
    Sum those gains, then deduct official FPL transfer-hit costs.

    Wildcard and Free Hit GWs are excluded because those moves are unlimited/
    temporary and are not comparable with ordinary transfers.
    """
    rows = []

    for _, r in s.iterrows():
        entry_id = int(r.entry_id)
        transfers = get_manager_transfers(entry_id) or []
        chips = _chip_map(entry_id)
        hist = get_manager_history(entry_id).get("current", [])
        hit_cost_by_gw = {
            int(h["event"]): abs(int(h.get("event_transfers_cost", 0)))
            for h in hist
        }

        transfer_gain = 0
        counted_transfers = 0
        used_gws = set()

        for t in transfers:
            gw = int(t.get("event", 0) or 0)
            if gw <= 0:
                continue

            # Exclude unlimited/temporary transfer windows.
            if chips.get(gw) in {"wildcard", "freehit"}:
                continue

            pts = _event_points_map(gw)
            element_in = int(t.get("element_in", 0) or 0)
            element_out = int(t.get("element_out", 0) or 0)

            in_points = pts.get(element_in, 0)
            out_points = pts.get(element_out, 0)

            transfer_gain += in_points - out_points
            counted_transfers += 1
            used_gws.add(gw)

        # Deduct the hit once per GW, not once per transfer record.
        hits_cost = sum(hit_cost_by_gw.get(gw, 0) for gw in used_gws)
        net = transfer_gain - hits_cost

        eligible = counted_transfers >= 10

        rows.append({
            "entry_id": entry_id,
            "team_name": r.team_name,
            "manager_name": r.manager_name,
            "ordinary_transfers": counted_transfers,
            "gross_transfer_gain": transfer_gain,
            "hit_cost": hits_cost,
            "net_transfer_gain": net,
            "eligible": "Yes" if eligible else "No",
            # Keep legacy fields for compatibility with any existing views.
            "transfer_gain": transfer_gain,
            "hits_cost": hits_cost,
            "transfer_count": counted_transfers,
            "net_transfer_points": net,
        })

    return (
        pd.DataFrame(rows)
        .sort_values(
            ["eligible", "net_transfer_gain", "gross_transfer_gain"],
            ascending=[False, False, False]
        )
        .reset_index(drop=True)
        if rows else pd.DataFrame()
    )

def captain_points_table(s):
    """
    Sum normal captain contribution across gameweeks.
    Triple Captain GWs are capped at the normal 2x captain contribution here,
    because the extra TC benefit has its own chip award.
    """
    rows = []

    for _, r in s.iterrows():
        entry_id = int(r.entry_id)
        hist = get_manager_history(entry_id).get("current", [])
        total = 0

        for h in hist:
            gw = int(h["event"])
            try:
                picks = get_manager_picks(entry_id, gw).get("picks", [])
                captain = next((p for p in picks if p.get("is_captain")), None)
                if not captain:
                    continue
                pts = _event_points_map(gw).get(int(captain["element"]), 0)
                # Normal captain contribution only. TC extra is excluded.
                total += pts * 2
            except Exception:
                continue

        rows.append({
            "entry_id": entry_id,
            "team_name": r.team_name,
            "manager_name": r.manager_name,
            "captain_points": total,
        })

    return (
        pd.DataFrame(rows)
        .sort_values("captain_points", ascending=False)
        .reset_index(drop=True)
        if rows else pd.DataFrame()
    )

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
    d = histories(s)
    out = {}
    if d.empty:
        return out

    # Mid-season standings: cumulative official FPL score through GW19.
    m = (
        d[d.GW <= 19]
        .groupby(["entry_id", "team_name", "manager_name"], as_index=False)
        .points.sum()
        .sort_values("points", ascending=False)
    )
    out["Mid Season Champion"] = m

    # Most bench points: exclude Bench Boost gameweeks because those points
    # were activated rather than truly left unused.
    bench_rows = []
    for _, r in s.iterrows():
        entry_id = int(r.entry_id)
        bb_gws = {
            int(c["event"])
            for c in get_manager_history(entry_id).get("chips", [])
            if c.get("name") == "bboost"
        }
        x = d[(d.entry_id == entry_id) & (~d.GW.isin(bb_gws))]
        bench_rows.append({
            "entry_id": entry_id,
            "team_name": r.team_name,
            "manager_name": r.manager_name,
            "bench_points": int(x.bench_points.sum()) if not x.empty else 0,
        })
    out["Most Bench Points"] = (
        pd.DataFrame(bench_rows).sort_values("bench_points", ascending=False)
        if bench_rows else pd.DataFrame()
    )

    # Biggest Climb = H2 scoring output - H1 scoring output.
    h1 = d[d.GW <= 19].groupby("entry_id").points.sum()
    h2 = d[d.GW >= 20].groupby("entry_id").points.sum()
    base = s[["entry_id", "team_name", "manager_name"]].copy()
    base["h1"] = base.entry_id.map(h1).fillna(0)
    base["h2"] = base.entry_id.map(h2).fillna(0)
    base["climb_score"] = base.h2 - base.h1
    out["Biggest Climb"] = base.sort_values("climb_score", ascending=False)

    # Most Captain Points: actual captain player points, normalised to 2x.
    out["Most Captain Points"] = captain_points_table(s)

    # Highest GW without any chip.
    no_chip = []
    for _, r in s.iterrows():
        entry_id = int(r.entry_id)
        chips = set(_chip_map(entry_id).keys())
        hist = get_manager_history(entry_id).get("current", [])
        for h in hist:
            gw = int(h["event"])
            if gw not in chips:
                no_chip.append({
                    "entry_id": entry_id,
                    "team_name": r.team_name,
                    "manager_name": r.manager_name,
                    "GW": gw,
                    "points": int(h.get("points", 0)),
                })

    out["Highest GW Without Chip"] = (
        pd.DataFrame(no_chip)
        .sort_values("points", ascending=False)
        .groupby("entry_id", as_index=False)
        .head(1)
        .sort_values("points", ascending=False)
        if no_chip else pd.DataFrame()
    )

    # Comeback King: actual league-position gain from GW19 to current/final.
    if not m.empty:
        mr = m.sort_values("points", ascending=False).reset_index(drop=True)
        mr["gw19_rank"] = mr["points"].rank(method="min", ascending=False).astype(int)
        cb = s[["entry_id", "team_name", "manager_name", "current_rank"]].merge(
            mr[["entry_id", "gw19_rank"]], on="entry_id", how="left"
        )
        cb["places_gained"] = cb.gw19_rank - cb.current_rank
        out["Comeback King"] = cb.sort_values("places_gained", ascending=False)

    # Mr Consistent: lowest SD of weekly GW rank among current/final top 10.
    ranks = []
    for gw, x in d.groupby("GW"):
        x = x.copy()
        x["gw_rank"] = x["points"].rank(method="min", ascending=False)
        ranks.append(x[["entry_id", "gw_rank"]])

    rr = pd.concat(ranks) if ranks else pd.DataFrame()
    if not rr.empty:
        cons = (
            rr.groupby("entry_id").gw_rank.std().reset_index(name="rank_volatility")
            .merge(
                s[["entry_id", "team_name", "manager_name", "current_rank"]],
                on="entry_id"
            )
        )
        cons = cons[cons.current_rank <= 10].sort_values("rank_volatility")
        out["Mr Consistent"] = cons

    out["Transfer Efficiency"] = transfer_efficiency(s)

    # Correct Transfer Tactician calculation.
    out["Transfer Tactician"] = transfer_tactician_table(s)

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
