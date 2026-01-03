import os
import base64
import json
import time
import requests
from playwright.sync_api import sync_playwright

# ================== Telegram ==================
TG_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(msg):
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": TG_CHAT_ID, "text": msg}
    )

# ================== Cookie ==================
def load_cookie_from_secret(context, secret_name):
    raw = os.getenv(secret_name)
    if not raw:
        raise RuntimeError(f"COOKIE_SECRET_MISSING::{secret_name}")

    data = base64.b64decode(raw).decode()
    state = json.loads(data)
    context.add_cookies(state["cookies"])

# ================== Cookie 检测 ==================
def check_cookie_valid(page, acc_name):
    page.goto("https://dash.skybots.tech/dashboard/my-projects", timeout=60_000)
    page.wait_for_timeout(4000)

    url = page.url.lower()
    if any(x in url for x in ["login", "auth"]):
        raise RuntimeError(f"COOKIE_EXPIRED::{acc_name}")

    if page.locator("text=Discord").count() > 0:
        raise RuntimeError(f"COOKIE_EXPIRED::{acc_name}")

# ================== 续期 ==================
def renew_vps(page, acc_name):
    page.wait_for_selector("button:has-text('Renouveler')", timeout=15_000)
    btn = page.locator("button:has-text('Renouveler')").first
    btn.scroll_into_view_if_needed()
    time.sleep(1)
    btn.click()
    time.sleep(6)

# ================== 主流程 ==================
def main():
    ACCOUNTS = [
        {"name": "ACC1", "cookie_secret": "SKYBOTS_COOKIE_ACC1"},
        # 多账号在这里继续加
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        page = context.new_page()

        for acc in ACCOUNTS:
            name = acc["name"]
            try:
                load_cookie_from_secret(context, acc["cookie_secret"])
                check_cookie_valid(page, name)
                renew_vps(page, name)

                send_telegram(f"✅ skybotVPS 续期成功\n账号：{name}")

            except RuntimeError as e:
                msg = str(e)

                if msg.startswith("COOKIE_EXPIRED"):
                    send_telegram(
                        f"⚠️ SkyBots Cookie 已失效\n"
                        f"账号：{name}\n"
                        f"请重新 Discord 登录并更新 Cookie"
                    )
                else:
                    send_telegram(
                        f"❌ skybotVPS 续期失败\n"
                        f"账号：{name}\n原因：{msg}"
                    )

        browser.close()

if __name__ == "__main__":
    main()
