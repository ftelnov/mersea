import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
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


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/events":
            self._handle_sse()
        else:
            self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode()
        try:
            code = serde.decode(body)
            self.server.mersea.write_from_browser(code)
            self.send_response(200)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
        except Exception as e:
            self.send_response(500)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _handle_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        mersea = self.server.mersea
        last_seen = mersea.version
        try:
            while not mersea.stopped.is_set():
                mersea.changed.wait(timeout=1)
                if mersea.version > last_seen:
                    last_seen = mersea.version
                    fragment = mersea.current_fragment
                    self.wfile.write(f"data: {fragment}\n\n".encode())
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def log_message(self, format, *args):
        pass


class _MerseaState:
    """Shared state between file watcher, HTTP server, and browser."""

    def __init__(self, path: Path):
        self.path = path
        self.current_fragment = serde.encode(path.read_text())
        self.version = 0
        self.changed = threading.Event()
        self.stopped = threading.Event()
        self._last_browser_content = None
        self._lock = threading.Lock()

    def write_from_browser(self, code: str):
        """Browser saved — write file, mark content to skip in watcher."""
        with self._lock:
            self._last_browser_content = code
            self.path.write_text(code)
            self.current_fragment = serde.encode(code)

    def check_file(self):
        """Called by file watcher. If file changed externally, update fragment."""
        try:
            code = self.path.read_text()
        except OSError:
            return
        with self._lock:
            if self._last_browser_content is not None and code == self._last_browser_content:
                self._last_browser_content = None
                return
            self._last_browser_content = None
        fragment = serde.encode(code)
        if fragment != self.current_fragment:
            self.current_fragment = fragment
            self.version += 1
            self.changed.set()
            self.changed.clear()


def _watch_file(state: _MerseaState):
    """Poll file for changes every 500ms."""
    last_mtime = 0.0
    while not state.stopped.is_set():
        try:
            mtime = os.path.getmtime(state.path)
        except OSError:
            mtime = 0.0
        if mtime != last_mtime:
            last_mtime = mtime
            state.check_file()
        state.stopped.wait(0.5)


def run(file_path: str) -> None:
    path = Path(file_path).resolve()
    state = _MerseaState(path)

    server = HTTPServer(("127.0.0.1", 0), _Handler)
    server.mersea = state
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    threading.Thread(target=_watch_file, args=(state,), daemon=True).start()

    ext_dir = tempfile.mkdtemp(prefix="mersea-ext-")
    USER_DATA.mkdir(parents=True, exist_ok=True)
    try:
        Path(ext_dir, "manifest.json").write_text(MANIFEST)
        content_js = CONTENT_JS.read_text().replace("__MERSEA_PORT__", str(port))
        Path(ext_dir, "content.js").write_text(content_js)

        url = f"{BASE_URL}#{state.current_fragment}"
        chromium = _find_chromium()
        proc = subprocess.Popen([
            chromium,
            f"--user-data-dir={USER_DATA}",
            f"--disable-extensions-except={ext_dir}",
            f"--load-extension={ext_dir}",
            "--enable-extensions",
            "--start-maximized",
            "--app=" + url,
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-infobars",
            "--disable-session-crashed-bubble",
            "--disable-component-update",
            "--disable-backgrounding-occluded-windows",
            "--disable-features=TranslateUI",
            "--noerrdialogs",
        ])
        proc.wait()
    finally:
        state.stopped.set()
        server.shutdown()
        shutil.rmtree(ext_dir, ignore_errors=True)
