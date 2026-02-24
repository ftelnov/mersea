import asyncio
import shutil
from pathlib import Path

from playwright.async_api import async_playwright

from mersea import serde

BROWSER_DATA = Path.home() / ".local" / "share" / "mersea" / "browser-data"
INJECT_JS = Path(__file__).parent / "assets" / "inject.js"
BASE_URL = "https://mermaid.ai/play"


def _find_chromium() -> str | None:
    for name in ("chromium", "chromium-browser", "google-chrome-stable", "google-chrome"):
        path = shutil.which(name)
        if path:
            return path
    return None


async def open_editor(file_path: str, headless: bool = False) -> None:
    path = Path(file_path).resolve()
    code = path.read_text()
    fragment = serde.encode(code)
    url = f"{BASE_URL}#{fragment}"

    BROWSER_DATA.mkdir(parents=True, exist_ok=True)

    chromium = _find_chromium()

    async with async_playwright() as pw:
        context = await pw.chromium.launch_persistent_context(
            user_data_dir=str(BROWSER_DATA),
            headless=headless,
            executable_path=chromium,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized",
            ],
            no_viewport=True,
        )

        page = context.pages[0] if context.pages else await context.new_page()

        async def save_callback(hash_str: str) -> None:
            try:
                code = serde.decode(hash_str)
                path.write_text(code)
                await page.evaluate("window.mersea_toast('Saved \u2713')")
            except Exception as e:
                await page.evaluate(
                    f"window.mersea_toast('Save failed: {e}', true)"
                )

        await page.expose_function("mersea_save", save_callback)
        await page.goto(url, wait_until="domcontentloaded")

        # Use evaluate() instead of add_script_tag() to bypass CSP
        inject_code = INJECT_JS.read_text()
        await page.evaluate(inject_code)

        # Exit when page or browser is closed
        closed = asyncio.Event()
        page.on("close", lambda _: closed.set())
        context.on("close", lambda _: closed.set())
        await closed.wait()

        try:
            await context.close()
        except Exception:
            pass


def run(file_path: str) -> None:
    asyncio.run(open_editor(file_path))
