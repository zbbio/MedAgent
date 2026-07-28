"""Manual browser smoke test against a running local MedAgent server."""

from pathlib import Path
import sys

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import config


SCREENSHOT = Path(__file__).resolve().parents[1] / ".medagent-e2e.png"


def main() -> None:
    edge = next(
        (
            path
            for path in (
                Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
                Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            )
            if path.exists()
        ),
        None,
    )
    if edge is None:
        raise RuntimeError("Microsoft Edge is not installed")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True, executable_path=str(edge))
        page = browser.new_page(viewport={"width": 1440, "height": 960})
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        page.get_by_role("heading", name="进入 MedAgent").wait_for()

        page.get_by_label("访问密码").fill("incorrect")
        page.get_by_role("button", name="进入助手").click()
        page.get_by_text("访问密码错误").wait_for()

        page.get_by_label("访问密码").fill(config.ACCESS_PASSWORD)
        page.get_by_role("button", name="进入助手").click()
        page.get_by_role("heading", name="欢迎使用 MedAgent").wait_for()

        page.get_by_title("系统统计").click()
        page.get_by_text("125,847").wait_for()
        page.screenshot(path=str(SCREENSHOT), full_page=True)
        page.locator(".modal-content .close-btn").click()
        page.get_by_role("button", name="退出登录").click()
        page.get_by_role("heading", name="进入 MedAgent").wait_for()
        browser.close()

    print(f"E2E_OK screenshot={SCREENSHOT}")


if __name__ == "__main__":
    main()
