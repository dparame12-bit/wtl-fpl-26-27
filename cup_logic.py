import os, json, random
import pandas as pd
from fpl_api import get_manager_history

DATA_DIR = "data"
CUP_FILE = os.path.join(DATA_DIR, "cup_draw.json")
RIVALRY_FILE = os.path.join(DATA_DIR, "rivalry_draw.json")

def _gw_points(entry_id, gws):
    hist = get_manager_history(int(entry_id)).get("current", [])
    return sum(int(h.get("points",0)) for h in hist if int(h.get("event",0)) in gws)

def cup_bracket(standings):
    if len(standings) < 20:
        return pd.DataFrame(), "Draw pending — WTL Cup draw will be generated once all 20 managers have joined."
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(CUP_FILE):
        ids = standings["entry_id"].astype(int).tolist(); random.shuffle(ids)
        # 8 managers play R1; 12 receive byes. R1 produces 4 winners -> 16 in R2.
        draw = {"r1_players": ids[:8], "byes": ids[8:]}
        with open(CUP_FILE,"w") as f: json.dump(draw,f)
    draw=json.load(open(CUP_FILE))
    name=dict(zip(standings.entry_id.astype(int), standings.team_name))
    rows=[]
    for i in range(0,8,2):
        a,b=draw["r1_players"][i:i+2]
        rows.append({"Round":"Play-in","GWs":"19–20","Fixture":f"{name.get(a,a)} vs {name.get(b,b)}","A Points":_gw_points(a,[19,20]),"B Points":_gw_points(b,[19,20])})
    for x in draw["byes"]:
        rows.append({"Round":"Bye","GWs":"19–20","Fixture":name.get(x,x),"A Points":"—","B Points":"—"})
    return pd.DataFrame(rows), "4 play-in fixtures + 12 byes → Round of 16 → Quarter-finals → Semi-finals → Final. Each tie spans 2 GWs."

def rivalry_draw(standings):
    if len(standings) < 20:
        return pd.DataFrame(), "Draw pending — Rivalry Week fixtures will be generated once all 20 managers have joined."
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(RIVALRY_FILE):
        ids=standings["entry_id"].astype(int).tolist()
        data={}
        for gw in (10,30):
            x=ids.copy(); random.shuffle(x); data[str(gw)]=[[x[i],x[i+1]] for i in range(0,20,2)]
        json.dump(data,open(RIVALRY_FILE,"w"))
    data=json.load(open(RIVALRY_FILE)); name=dict(zip(standings.entry_id.astype(int),standings.team_name))
    rows=[]
    for gw,pairs in data.items():
        for n,(a,b) in enumerate(pairs,1):
            pa,pb=_gw_points(a,[int(gw)]),_gw_points(b,[int(gw)])
            winner=name.get(a,a) if pa>pb else name.get(b,b) if pb>pa else "Tie"
            rows.append({"GW":int(gw),"Match":n,"Manager A":name.get(a,a),"A Points":pa,"Manager B":name.get(b,b),"B Points":pb,"Winner":winner,"Prize":50 if winner!="Tie" else 25})
    return pd.DataFrame(rows), "10 head-to-head fixtures in GW10 and GW30. Each winner earns ₹50; a tie splits the ₹50."
