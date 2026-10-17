#!/usr/bin/env python3
"""矢印キー/スペースキーの入力確認用 SB3 を生成する(外部依存なし)。
- 矢印キー(sensing_keypressed): 押している間 5px/フレームで移動(同時押しで斜め)
- スペース(event_whenkeypressed): spaceCount を+1し、色効果を変えて吹き出しに回数を表示
"""
import hashlib, json, zipfile, pathlib, sys

out = pathlib.Path(__file__).resolve().parent.parent / "test" / "keytest.sb3"

backdrop = ('<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">'
            '<rect width="480" height="360" fill="#f4f6ff"/>'
            '<path d="M240 0V360M0 180H480" stroke="#b9c2e8" stroke-width="2"/></svg>').encode()
ball = ('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40">'
        '<circle cx="20" cy="20" r="18" fill="#e8553d" stroke="#222" stroke-width="2"/>'
        '<circle cx="27" cy="14" r="3.5" fill="#fff"/></svg>').encode()
md5 = lambda b: hashlib.md5(b).hexdigest()
bd_md5, ball_md5 = md5(backdrop), md5(ball)

def blk(opcode, parent=None, nxt=None, inputs=None, fields=None, top=False, shadow=False, **extra):
    b = {"opcode": opcode, "next": nxt, "parent": parent, "inputs": inputs or {}, "fields": fields or {},
         "shadow": shadow, "topLevel": top}
    if top: b["x"], b["y"] = 20, 20
    b.update(extra)
    return b

num = lambda v: [1, [4, str(v)]]
txt = lambda v: [1, [10, str(v)]]

blocks = {}
# --- 緑の旗: 初期化 + 矢印キー監視ループ ---
blocks["flag"] = blk("event_whenflagclicked", nxt="goto", top=True)
blocks["goto"] = blk("motion_gotoxy", "flag", "setv", {"X": num(0), "Y": num(0)})
blocks["setv"] = blk("data_setvariableto", "goto", "ge", {"VALUE": txt(0)}, {"VARIABLE": ["spaceCount", "v1"]})
blocks["ge"] = blk("looks_cleargraphiceffects", "setv", "fv")
blocks["fv"] = blk("control_forever", "ge", None, {"SUBSTACK": [2, "if_l"]})
dirs = [("l", "left arrow", "motion_changexby", "DX", -5, "if_r"),
        ("r", "right arrow", "motion_changexby", "DX", 5, "if_u"),
        ("u", "up arrow", "motion_changeyby", "DY", 5, "if_d"),
        ("d", "down arrow", "motion_changeyby", "DY", -5, None)]
for i, (n, keyname, op, arg, val, nxt) in enumerate(dirs):
    parent = "fv" if i == 0 else "if_" + dirs[i-1][0]
    blocks["if_" + n] = blk("control_if", parent, nxt, {"CONDITION": [2, "k_" + n], "SUBSTACK": [2, "m_" + n]})
    blocks["k_" + n] = blk("sensing_keypressed", "if_" + n, None, {"KEY_OPTION": [1, "km_" + n]})
    blocks["km_" + n] = blk("sensing_keyoptions", "k_" + n, None, None, {"KEY_OPTION": [keyname, None]}, shadow=True)
    blocks["m_" + n] = blk(op, "if_" + n, None, {arg: num(val)})
# --- スペースキー ---
blocks["sp"] = blk("event_whenkeypressed", None, "inc", None, {"KEY_OPTION": ["space", None]}, top=True)
blocks["inc"] = blk("data_changevariableby", "sp", "eff", {"VALUE": num(1)}, {"VARIABLE": ["spaceCount", "v1"]})
blocks["eff"] = blk("looks_changeeffectby", "inc", "say", {"CHANGE": num(25)}, {"EFFECT": ["COLOR", None]})
blocks["say"] = blk("looks_sayforsecs", "eff", None, {"MESSAGE": [3, "join", [10, ""]], "SECS": num(0.5)})
blocks["join"] = blk("operator_join", "say", None,
                     {"STRING1": txt("SPACE x"), "STRING2": [3, [12, "spaceCount", "v1"], [10, ""]]})

def costume(name, md5v, fmt, cx, cy):
    return {"assetId": md5v, "name": name, "md5ext": f"{md5v}.{fmt}", "dataFormat": fmt,
            "rotationCenterX": cx, "rotationCenterY": cy}

stage = {"isStage": True, "name": "Stage", "variables": {}, "lists": {}, "broadcasts": {}, "blocks": {},
         "comments": {}, "currentCostume": 0, "costumes": [costume("backdrop1", bd_md5, "svg", 240, 180)],
         "sounds": [], "volume": 100, "layerOrder": 0, "tempo": 60, "videoTransparency": 50,
         "videoState": "on", "textToSpeechLanguage": None}
sprite = {"isStage": False, "name": "Player", "variables": {"v1": ["spaceCount", 0]}, "lists": {},
          "broadcasts": {}, "blocks": blocks, "comments": {}, "currentCostume": 0,
          "costumes": [costume("ball", ball_md5, "svg", 20, 20)], "sounds": [], "volume": 100,
          "layerOrder": 1, "visible": True, "x": 0, "y": 0, "size": 100, "direction": 90,
          "draggable": False, "rotationStyle": "all around"}
project = {"targets": [stage, sprite], "monitors": [], "extensions": [],
           "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "turboboost-test"}}

# 参照整合性チェック
ids = set(blocks)
for bid, b in blocks.items():
    for ref in (b["next"], b["parent"]):
        assert ref is None or ref in ids, (bid, ref)
    for v in b["inputs"].values():
        for part in v[1:]:
            if isinstance(part, str): assert part in ids, (bid, part)

out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("project.json", json.dumps(project, ensure_ascii=False))
    z.writestr(f"{bd_md5}.svg", backdrop)
    z.writestr(f"{ball_md5}.svg", ball)
print("wrote", out, out.stat().st_size, "bytes;", len(blocks), "blocks")
