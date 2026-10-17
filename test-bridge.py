#!/usr/bin/env python3
"""仮想キーボード→postIOData の押下/解放ロジックを、本物のChromiumのタッチ/ポインター入力で検証する。
VMは偽物(呼び出し記録のみ)。Scratch実体での確認は index.html の「自己診断」で行う。"""
import subprocess, time, sys, pathlib
from playwright.sync_api import sync_playwright

root = pathlib.Path(__file__).resolve().parent.parent
srv = subprocess.Popen([sys.executable, "-m", "http.server", "8765"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(0.8)
results = []
def check(name, ok, detail=""):
    results.append(ok); print(("PASS " if ok else "FAIL ") + name + (("  " + detail) if detail else ""))

try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 1100, "height": 500}, has_touch=True)
        page = ctx.new_page()
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto("http://localhost:8765/test/bridge-test.html")
        cdp = ctx.new_cdp_session(page)
        calls = lambda: page.evaluate("window.calls")
        clear = lambda: page.evaluate("window.calls.length = 0")
        def center(key):
            return page.evaluate("""k => { const r=[...document.querySelectorAll('.vk-key')].find(e=>e.dataset.key===k).getBoundingClientRect();
                return {x:r.x+r.width/2, y:r.y+r.height/2}; }""", key)
        def touch(type_, pts):
            cdp.send("Input.dispatchTouchEvent", {"type": type_, "touchPoints": pts})
        tp = lambda k, i: {**center(k), "id": i}

        # 1) 単一タッチ: 押下→解放
        clear(); touch("touchStart", [tp("ArrowRight", 1)]); touch("touchEnd", [])
        check("単一タッチで isDown:true → isDown:false を1回ずつ", calls() == [["keyboard","ArrowRight",True],["keyboard","ArrowRight",False]], str(calls()))

        # 2) マルチタッチ同時押し (→ + ↑ + Space)、片方だけ離す
        clear(); touch("touchStart", [tp("ArrowRight",1), tp("ArrowUp",2), tp(" ",3)])
        c = calls(); check("3キー同時押しで3つとも押下送信", sorted(x[1] for x in c if x[2]) == [" ","ArrowRight","ArrowUp"], str(c))
        touch("touchEnd", [tp("ArrowRight",1), tp(" ",3)])
        up = [x[1] for x in calls() if not x[2]]
        rel = sorted(x[1] for x in calls() if not x[2])
        check("2本離すとその2キーだけ解放(↑は押下継続)", rel == [" ", "ArrowRight"] and page.evaluate("bridge.pressed()") == ["ArrowUp"], f"released={rel} pressed={page.evaluate('bridge.pressed()')}")
        touch("touchEnd", []); 
        check("全部離すと押下中ゼロ", page.evaluate("bridge.pressed()") == [], str(page.evaluate("bridge.pressed()")))

        # 3) タッチ中に指を別の場所へ動かして離す(キー外で離しても解放)
        clear(); touch("touchStart", [tp("ArrowLeft",1)])
        touch("touchMove", [{"x": 5, "y": 5, "id": 1}]); touch("touchEnd", [])
        check("キー外へスライドして離しても解放", page.evaluate("bridge.pressed()") == [] and calls()[-1] == ["keyboard","ArrowLeft",False], str(calls()))

        # 4) touchCancel
        clear(); touch("touchStart", [tp("ArrowDown",1)]); touch("touchCancel", [])
        check("touchCancel(システムによる中断)で解放", page.evaluate("bridge.pressed()") == [] and calls()[-1][2] is False, str(calls()))

        # 5) マウス(PC)
        clear(); c0 = center("ArrowUp"); page.mouse.move(c0["x"], c0["y"]); page.mouse.down(); page.mouse.move(2, 2); page.mouse.up()
        check("マウス押下→キー外で離しても解放", calls() == [["keyboard","ArrowUp",True],["keyboard","ArrowUp",False]], str(calls()))

        # 6) フォーカス喪失 / 非表示 / レイアウト切替
        for label, js in [("window blur", "window.dispatchEvent(new Event('blur'))"),
                          ("pagehide", "window.dispatchEvent(new Event('pagehide'))"),
                          ("レイアウト切替", "vk.setLayout('us')")]:
            clear(); touch("touchStart", [tp("ArrowRight",1)])
            page.evaluate(js)
            check(f"{label} で押しっぱなしを解放", page.evaluate("bridge.pressed()") == [] and calls()[-1] == ["keyboard","ArrowRight",False], str(calls()))
            touch("touchEnd", [])
            check(f"{label} 後の touchEnd で二重解放しない", calls()[-1] == ["keyboard","ArrowRight",False] and len(calls()) == 2, str(calls()))
            page.evaluate("vk.setLayout('jp')")

        # 7) 3レイアウトすべてで矢印が十字配置
        for lid in ["jp", "us", "sym"]:
            page.evaluate(f"vk.setLayout('{lid}')")
            r = page.evaluate("""() => { const g=k=>{const e=document.querySelector('.vk-key.arrow[data-key='+k+']'); const r=e.getBoundingClientRect(); return {cx:r.x+r.width/2, cy:r.y+r.height/2, w:r.width}};
                return {u:g('ArrowUp'), d:g('ArrowDown'), l:g('ArrowLeft'), r:g('ArrowRight')}; }""")
            ok = (abs(r["u"]["cx"]-r["d"]["cx"])<2 and r["u"]["cy"]<r["d"]["cy"] and abs(r["l"]["cy"]-r["d"]["cy"])<2
                  and abs(r["r"]["cy"]-r["d"]["cy"])<2 and r["l"]["cx"]<r["d"]["cx"]<r["r"]["cx"])
            check(f"レイアウト {lid}: 矢印が十字(逆T字)配置", ok, str({k:(round(v['cx']),round(v['cy'])) for k,v in r.items()}))
        check("ページエラーなし", not errs, str(errs))
        b.close()
finally:
    srv.terminate()
sys.exit(0 if all(results) else 1)
