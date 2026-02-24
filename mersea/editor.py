import json
import shutil
import subprocess
import tempfile
import threading
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from mersea import serde

BASE_URL = "https://mermaid.ai/play"
USER_DATA = Path.home() / ".local" / "share" / "mersea" / "browser-data"
MANIFEST = json.dumps({
    "manifest_version": 3,
    "name": "Mersea",
    "version": "1.0",
    "content_scripts": [{
        "matches": [
            "*://mermaid.ai/play*",
            "*://www.mermaidchart.com/play*",
            "*://mermaid.live/*",
        ],
        "js": ["content.js"],
        "run_at": "document_idle",
    }],
    "host_permissions": ["http://localhost/*"],
})
CONTENT_JS = Path(__file__).parent / "assets" / "content.js"


def _find_chromium() -> str:
    for name in ("chromium", "chromium-browser", "google-chrome-stable", "google-chrome"):
        path = shutil.which(name)
        if path:
            return path
    raise RuntimeError("Chromium not found on PATH")


class _SaveHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()

        try:
            code = serde.decode(body)
            self.server.target_path.write_text(code)
            self.send_response(200)
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode())
            return

        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        pass  # silence logs


def run(file_path: str) -> None:
    path = Path(file_path).resolve()
    code = path.read_text()
    fragment = serde.encode(code)
    url = f"{BASE_URL}#{fragment}"

    # Start HTTP server on random port
    server = HTTPServer(("127.0.0.1", 0), _SaveHandler)
    server.target_path = path
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    # Build temp extension with port baked in
    ext_dir = tempfile.mkdtemp(prefix="mersea-ext-")
    USER_DATA.mkdir(parents=True, exist_ok=True)
    try:
        Path(ext_dir, "manifest.json").write_text(MANIFEST)
        content_js = CONTENT_JS.read_text().replace("__MERSEA_PORT__", str(port))
        Path(ext_dir, "content.js").write_text(content_js)

        chromium = _find_chromium()
        proc = subprocess.Popen([
            chromium,
            f"--user-data-dir={USER_DATA}",
            f"--disable-extensions-except={ext_dir}",
            f"--load-extension={ext_dir}",
            "--enable-extensions",
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
            url,
        ])
        proc.wait()
    finally:
        server.shutdown()
        shutil.rmtree(ext_dir, ignore_errors=True)
