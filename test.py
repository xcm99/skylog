import base64
import json
import os
import time
import re
import requests
from playwright.sync_api import sync_playwright

# ========= 配置区 =========
TG_BOT = os.getenv("TG_BOT_TOKEN")
TG_CHAT = os.getenv("TG_CHAT_ID")
DASHBOARD = "https://dash.skybots.tech/dashboard/my-projects"

# 多账号配置：在此处添加更多账号环境变量
ACCOUNTS = [
    {"name": "账号1", "cookie": os.getenv("SKYBOTS_COOKIE_ACC1")},
    {"name": "账号2", "cookie": os.getenv("SKYBOTS_COOKIE_ACC2")},
    # {"name": "账号3", "cookie": os.getenv("SKYBOTS_COOKIE_ACC3")},
]

def tg(msg, photo_path=None):
    if not TG_BOT or not TG_CHAT:
        print(f"推送跳过：{msg}")
        return
    base_url = f"https://api.telegram.org/bot{TG_BOT}"
    try:
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as f:
                requests.post(f"{base_url}/sendPhoto", data={"chat_id": TG_CHAT, "caption": msg}, files={"photo": f}, timeout=30)
        else:
            requests.post(f"{base_url}/sendMessage", json={"chat_id": TG_CHAT, "text": msg}, timeout=15)
    except Exception as e:
        print(f"TG 发送失败: {e}")

def run_account(acc):
    name = acc["name"]
    if not acc.get("cookie"):
        print(f"⏩ {name}: 未配置 Cookie，跳过")
        return

    try:
        state = json.loads(base64.b64decode(acc["cookie"]).decode("utf-8"))
    except Exception as e:
        print(f"❌ {name} Cookie 解码失败: {e}")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=state)
        page = context.new_page()

        print(f"🚀 正在处理: {name}...")
        try:
            page.goto(DASHBOARD, timeout=60_000, wait_until="networkidle")
            time.sleep(8)
            
            # 登录校验
            if "/login" in page.url:
                tg(f"⚠️ {name} 登录失效，请更新 Cookie")
                browser.close()
                return

            # 强制进入项目页
            if "my-projects" not in page.url:
                page.get_by_role("link", name=re.compile(r"Mes Projets|My Projects", re.I)).click()
                time.sleep(5)

            # 查找续期按钮
            renew_selector = "button:has-text('Renouveler'), button:has-text('Renew'), button:has-text('续期')"
            renew_buttons = page.locator(renew_selector)
            count = renew_buttons.count()

            shot_path = f"status_{name}.png"
            
            if count == 0:
                page.screenshot(path=shot_path, full_page=True)
                tg(f"ℹ️ {name}: 未发现续期项目。", photo_path=shot_path)
            else:
                # 执行续期
                success_count = 0
                for i in range(count):
                    btn = renew_buttons.nth(i)
                    if btn.is_visible():
                        btn.scroll_into_view_if_needed()
                        btn.click()
                        time.sleep(5)
                        success_count += 1
                
                # 续期成功后截图，确认按钮是否消失或变色
                page.screenshot(path=shot_path, full_page=True)
                tg(f"✅ {name}: 续期成功！执行了 {success_count} 个项目。", photo_path=shot_path)

            if os.path.exists(shot_path):
                os.remove(shot_path)

        except Exception as e:
            print(f"❌ {name} 运行出错: {e}")
        finally:
            browser.close()

def main():
    for acc in ACCOUNTS:
        run_account(acc)
    with open("heartbeat.txt", "w") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()
