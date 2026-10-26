"""Take high-resolution screenshots of every tab of the running app (headless Chrome, DevTools protocol).

    python scripts/capture_screens.py [app_url] [output_dir]

Needs the app running (e.g. python scripts/launch.py --no-browser --port 8502) and Chrome or Edge installed.
The AI coach shot waits for the real local model, so it can take a few minutes on a CPU.
"""

from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websocket

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8502"
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else Path(__file__).resolve().parents[1] / "deliverables" / "assets" / "screens")
OUT.mkdir(parents=True, exist_ok=True)
BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
PORT = 9333


class Page:
    def __init__(self) -> None:
        exe = next(p for p in BROWSERS if Path(p).exists())
        self.proc = subprocess.Popen([exe, "--headless=new", f"--remote-debugging-port={PORT}", "--hide-scrollbars", "--disable-gpu",
                                      f"--user-data-dir={tempfile.mkdtemp()}", "--window-size=1440,1000", "about:blank"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                targets = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json"))
                self.ws = websocket.create_connection(next(t for t in targets if t["type"] == "page")["webSocketDebuggerUrl"], timeout=120)
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.5)
        self.n = 0

    def call(self, method: str, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == self.n:
                return message.get("result", {})

    def js(self, expression: str):
        result = self.call("Runtime.evaluate", expression=expression, returnByValue=True, awaitPromise=True)
        return result.get("result", {}).get("value")

    def wait_for(self, expression: str, timeout: float = 120) -> bool:
        end = time.time() + timeout
        while time.time() < end:
            if self.js(expression):
                return True
            time.sleep(1)
        return False

    def shot(self, name: str, width: int = 1440) -> None:
        height = self.js("Math.max(document.documentElement.scrollHeight, (document.querySelector('[data-testid=stMain]')||{}).scrollHeight||0)") or 1000
        height = int(min(max(height, 900), 5200))
        self.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=1.5, mobile=False)
        time.sleep(2)
        data = self.call("Page.captureScreenshot", format="png")["data"]
        (OUT / f"{name}.png").write_bytes(base64.b64decode(data))
        print(f"saved {name}.png ({width}x{height} @1.5x)", flush=True)

    def click_tab(self, label: str) -> None:
        found = self.js("""(() => {
            const wanted = %s;
            const nodes = [...document.querySelectorAll('[role="tab"], [data-baseweb="tab"]')];
            const tab = nodes.find(n => (n.innerText || '').trim() === wanted);
            if (!tab) return 'tabs seen: ' + nodes.map(n => (n.innerText || '').trim()).join(' | ');
            tab.scrollIntoView(); tab.click(); return 'clicked';
        })()""" % json.dumps(label))
        print(f"tab {label!r}: {found}", flush=True)
        time.sleep(4)

    def click_button(self, label: str) -> None:
        found = self.js("""(() => {
            const wanted = %s;
            const b = [...document.querySelectorAll('button')].find(n => (n.innerText || '').trim() === wanted);
            if (!b) return 'button not found';
            b.scrollIntoView(); b.click(); return 'clicked';
        })()""" % json.dumps(label))
        print(f"button {label!r}: {found}", flush=True)


def main() -> None:
    page = Page()
    try:
        page.call("Page.enable")
        page.call("Emulation.setDeviceMetricsOverride", width=1440, height=1000, deviceScaleFactor=1.5, mobile=False)
        page.call("Page.navigate", url=URL)
        assert page.wait_for("document.body.innerText.includes('MODEL OUTPUT')", 240), "app did not render a forecast"
        time.sleep(6)
        only_ai = bool(__import__('os').environ.get('ONLY_AI'))
        if not only_ai:
            page.shot("01_forecast_studio")
        for label, name in () if only_ai else (("Best time", "02_best_time"), ("Title lab", "03_title_lab"), ("Similar videos", "05_similar_videos"),
                            ("Scenario lab", "06_scenario_lab"), ("Model brief", "07_model_brief")):
            page.click_tab(label)
            time.sleep(4)
            page.shot(name)
        page.click_tab("AI coach")
        page.click_button("Generate recommendations")
        done = page.wait_for("document.body.innerText.includes('Expected views (ML model)')", 600)
        print("AI coach finished:", done, flush=True)
        time.sleep(3)
        page.shot("04_ai_coach")
    finally:
        page.proc.terminate()


if __name__ == "__main__":
    main()
