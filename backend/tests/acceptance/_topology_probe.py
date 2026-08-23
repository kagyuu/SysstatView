"""配布トポロジー (静的配信 + /api リバースプロキシ) の再現検証。

nginx.conf と同じ経路構成を Python で再現し、ブラウザから見えるのと同じ
「同一オリジンで /api を叩く」形が実際に成立することを確認する。
Docker が無い環境で、P302 実行前チェック項目 7 を実地確認するためのもの。
"""
import http.server
import json
import socketserver
import threading
import urllib.request
import urllib.error
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DIST = REPO / "frontend" / "dist" / "sysstatview-frontend" / "browser"
API = "http://127.0.0.1:8000"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(DIST), **kw)

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/"):
            # nginx の proxy_pass http://api:8000; と同じ: URI を書き換えず前送り
            try:
                with urllib.request.urlopen(API + self.path, timeout=30) as r:
                    body, status = r.read(), r.status
            except urllib.error.HTTPError as e:
                body, status = e.read(), e.code
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        # SPA フォールバック: try_files $uri $uri/ /index.html;
        candidate = DIST / self.path.lstrip("/")
        if self.path != "/" and not candidate.exists():
            self.path = "/index.html"
        return super().do_GET()


def main():
    with socketserver.TCPServer(("127.0.0.1", 0), Handler) as httpd:
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{port}"
        results = {}

        def get(path):
            try:
                with urllib.request.urlopen(base + path, timeout=30) as r:
                    return r.status, r.read()
            except urllib.error.HTTPError as e:
                return e.code, e.read()

        s, b = get("/")
        results["GET / (index.html)"] = (s, b"<app-root" in b or b"app-root" in b)
        s, b = get("/graph/c2FyMjM")
        results["GET /graph/... (SPA フォールバック)"] = (s, b"app-root" in b)
        s, b = get("/api/health")
        results["GET /api/health (プロキシ)"] = (s, json.loads(b).get("status") == "ok")
        s, b = get("/api/log-files?from=2026-08-01&to=2026-08-31&perPage=100")
        d = json.loads(b)
        results["GET /api/log-files (プロキシ)"] = (s, d.get("totalItems", 0) > 0)
        first = d["items"][0]["fileId"]
        s, b = get(f"/api/log-files/{first}/metrics")
        d2 = json.loads(b)
        results["GET /api/log-files/{id}/metrics"] = (s, len(d2.get("groups", [])) > 0)
        s, b = get("/api/metric-catalog")
        results["GET /api/metric-catalog"] = (s, len(json.loads(b)["groups"]) > 0)

        ok = True
        for name, (status, valid) in results.items():
            mark = "OK " if (status == 200 and valid) else "NG "
            if not (status == 200 and valid):
                ok = False
            print(f"  {mark} {name}: HTTP {status}")
        print("TOPOLOGY_RESULT:" + ("PASS" if ok else "FAIL"))


if __name__ == "__main__":
    main()
