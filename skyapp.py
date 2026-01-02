import base64
import json
import os
import time
from playwright.sync_api import sync_playwright

# ========= Telegram =========
TG_BOT = os.getenv("TG_BOT_TOKEN")
TG_CHAT = os.getenv("TG_CHAT_ID")

def tg(msg):
    if not TG_BOT or not TG_CHAT:
        return
    import requests
    requests.post(
        f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
        json={"chat_id": TG_CHAT, "text": msg}
    )

# ========= 多账号 Cookie =========
ACCOUNTS = [
    {
        "name": "ACC1",
        "cookie": os.getenv("SKYBOTS_COOKIE_ACC1"),
    },
    # 如有更多账号继续加
]

DASHBOARD = "https://dash.skybots.tech/fr/dashboard/my-projects"

def run_account(acc):
    name = acc["name"]

    if not acc["cookie"]:
        raise RuntimeError(f"{name} 未配置 Cookie Secret")

    state = json.loads(
        base64.b64decode(acc["cookie"]).decode("utf-8")
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=state)
        page = context.new_page()

        page.goto(DASHBOARD, timeout=60_000)
        time.sleep(5)

        # Cookie 失效判断
        if "/login" in page.url:
            tg(f"⚠️ SkyBots 登录失效：{name}\n请重新 Discord 授权")
            raise RuntimeError("Cookie expired")

        print(f"✅ {name} 登录成功")

        # === 找 Renew 按钮 ===
        renew = page.locator("button:has-text('Renouveler')")
        if renew.count() == 0:
            tg(f"⚠️ {name} 未找到续期按钮")
            return

        renew.first.scroll_into_view_if_needed()
        time.sleep(1)
        renew.first.click()

        time.sleep(5)

        tg(f"✅ GREATVPS 续期成功\n账号：{name}")
        print(f"🎉 {name} 续期完成")

        browser.close()

def main():
    for acc in ACCOUNTS:
        try:
            run_account(acc)
        except Exception as e:
            print(f"❌ {acc['name']} 失败：{e}")

    # ===== 心跳，防 Action 停跑 =====
    with open("heartbeat.txt", "w") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()
