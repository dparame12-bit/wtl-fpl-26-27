import os
import json
import random
import pandas as pd

from config import TARGET_MANAGERS, PRIZES
from fpl_api import get_manager_history

DATA_DIR = "data"
CUP_FILE = os.path.join(DATA_DIR, "cup_draw.json")
RIVALRY_FILE = os.path.join(DATA_DIR, "rivalry_draw.json")


def _gw_points(entry_id, gws):
    hist = get_manager_history(int(entry_id)).get("current", [])
    return sum(
        int(h.get("points", 0))
        for h in hist
        if int(h.get("event", 0)) in gws
    )


def _current_ids(standings):
    return sorted(standings["entry_id"].astype(int).tolist())


def _valid_saved_ids(saved_ids, standings):
    return sorted(int(x) for x in saved_ids) == _current_ids(standings)


def cup_bracket(standings):
    """
    22-manager cup:
    - R32/play-in stage: 12 managers play 6 fixtures
    - 10 managers receive byes
    - 6 winners + 10 byes = 16 managers in the Round of 16
    """
    if len(standings) < TARGET_MANAGERS:
        return (
            pd.DataFrame(),
            f"Draw pending — WTL Cup draw will be generated once all {TARGET_MANAGERS} managers have joined.",
        )

    os.makedirs(DATA_DIR, exist_ok=True)

    regenerate = True
    draw = None
    if os.path.exists(CUP_FILE):
        try:
            with open(CUP_FILE, "r", encoding="utf-8") as f:
                draw = json.load(f)
            saved = draw.get("r1_players", []) + draw.get("byes", [])
            regenerate = not (
                len(draw.get("r1_players", [])) == 12
                and len(draw.get("byes", [])) == 10
                and _valid_saved_ids(saved, standings)
            )
        except Exception:
            regenerate = True

    if regenerate:
        ids = standings["entry_id"].astype(int).tolist()
        random.shuffle(ids)
        draw = {
            "format": "22_manager_v1",
            "r1_players": ids[:12],
            "byes": ids[12:],
        }
        with open(CUP_FILE, "w", encoding="utf-8") as f:
            json.dump(draw, f, indent=2)

    name = dict(zip(standings.entry_id.astype(int), standings.team_name))
    rows = []

    for i in range(0, 12, 2):
        a, b = draw["r1_players"][i:i + 2]
        rows.append({
            "Round": "Play-in",
            "GWs": "19–20",
            "Fixture": f"{name.get(a, a)} vs {name.get(b, b)}",
            "A Points": _gw_points(a, [19, 20]),
            "B Points": _gw_points(b, [19, 20]),
        })

    for x in draw["byes"]:
        rows.append({
            "Round": "Bye",
            "GWs": "19–20",
            "Fixture": name.get(x, x),
            "A Points": "—",
            "B Points": "—",
        })

    return (
        pd.DataFrame(rows),
        "6 play-in fixtures + 10 byes → Round of 16 → Quarter-finals → Semi-finals → Final. "
        "Each tie spans 2 GWs. Cup winner receives ₹1,500.",
    )


def rivalry_draw(standings):
    """
    Two Rivalry Weeks (GW10 and GW30).
    22 managers = 11 H2H fixtures per event.
    """
    if len(standings) < TARGET_MANAGERS:
        return (
            pd.DataFrame(),
            f"Draw pending — Rivalry Week fixtures will be generated once all {TARGET_MANAGERS} managers have joined.",
        )

    os.makedirs(DATA_DIR, exist_ok=True)

    data = None
    regenerate = True
    if os.path.exists(RIVALRY_FILE):
        try:
            with open(RIVALRY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            all_saved = []
            valid_shape = True
            for gw in ("10", "30"):
                pairs = data.get(gw, [])
                if len(pairs) != 11:
                    valid_shape = False
                    break
                for pair in pairs:
                    if len(pair) != 2:
                        valid_shape = False
                        break
                    all_saved.extend(pair)

            # Each GW contains the full roster once. Validate one GW's roster,
            # because all_saved contains each manager twice across the two events.
            gw10_ids = [eid for pair in data.get("10", []) for eid in pair]
            regenerate = not (
                valid_shape
                and _valid_saved_ids(gw10_ids, standings)
            )
        except Exception:
            regenerate = True

    if regenerate:
        ids = standings["entry_id"].astype(int).tolist()
        data = {}
        for gw in (10, 30):
            x = ids.copy()
            random.shuffle(x)
            data[str(gw)] = [
                [x[i], x[i + 1]]
                for i in range(0, TARGET_MANAGERS, 2)
            ]

        with open(RIVALRY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    name = dict(zip(standings.entry_id.astype(int), standings.team_name))
    rows = []

    for gw, pairs in data.items():
        for n, (a, b) in enumerate(pairs, 1):
            pa = _gw_points(a, [int(gw)])
            pb = _gw_points(b, [int(gw)])

            winner = (
                name.get(a, a)
                if pa > pb
                else name.get(b, b)
                if pb > pa
                else "Tie"
            )

            rows.append({
                "GW": int(gw),
                "Match": n,
                "Manager A": name.get(a, a),
                "A Points": pa,
                "Manager B": name.get(b, b),
                "B Points": pb,
                "Winner": winner,
                "Prize": PRIZES["rivalry_week"][int(gw)] if winner != "Tie" else PRIZES["rivalry_week"][int(gw)] / 2,
            })

    return (
        pd.DataFrame(rows),
        "11 head-to-head fixtures in GW10 and GW30. Each winner earns ₹50; a tie splits the ₹50.",
    )
