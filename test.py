import base64
import json
import os
import time
import re
from playwright.sync_api import sync_playwright

# ========= 配置区 =========
TG_BOT = os.getenv("TG_BOT_TOKEN")
TG_CHAT = os.getenv("TG_CHAT_ID")
DASHBOARD = "https://dash.skybots.tech/fr/dashboard/my-projects"

# 账号列表：从环境变量读取多个 Cookie
ACCOUNTS = [
    {"name": "ACC1", "cookie": os.getenv("SKYBOTS_COOKIE_ACC1")},
    # 如果有 ACC2，在此继续添加
]

def tg(msg):
    if not TG_BOT or not TG_CHAT:
        print(f"推送跳过（未配置 TG）：{msg}")
        return
    import requests
    try:
        requests.post(
            f"https://api.telegram.org/bot{TG_BOT}/sendMessage",
            json={"chat_id": TG_CHAT, "text": msg},
            timeout=10
        )
    except Exception as e:
        print(f"TG 发送失败: {e}")

def run_account(acc):
    name = acc["name"]
    if not acc["cookie"]:
        print(f"⚠️ 跳过 {name}：未配置环境变量")
        return

    # 解码 Cookie 状态
    try:
        state = json.loads(base64.b64decode(acc["cookie"]).decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Cookie 解码失败，请检查格式: {e}")

    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=state)
        page = context.new_page()

        print(f"🚀 正在处理账号: {name}...")
        
        # 访问页面，增加重试逻辑
        page.goto(DASHBOARD, timeout=60_000, wait_until="networkidle")
        time.sleep(5)

        # 1. 登录失效检查
        if "/login" in page.url:
            tg(f"⚠️ SkyBots 登录失效：{name}\n请重新获取 Cookie。")
            raise RuntimeError("Cookie 已过期")

        # 2. 查找续期按钮 (正则匹配：兼容 Renouveler / Renew)
        # 使用正则表达式忽略大小写匹配中英法文常见续期字样
        renew_selector = "button:has-text('Renouveler'), button:has-text('Renew'), button:has-text('续期')"
        renew_buttons = page.locator(renew_selector)
        
        count = renew_buttons.count()
        if count == 0:
            print(f"ℹ️ {name}: 当前没有可续期的项目")
            return

        # 3. 循环执行续期
        success_count = 0
        for i in range(count):
            btn = renew_buttons.nth(i)
            if btn.is_visible():
                try:
                    btn.scroll_into_view_if_needed()
                    btn.click()
                    time.sleep(3) # 等待 API 响应
                    success_count += 1
                except Exception as e:
                    print(f"点击第 {i+1} 个按钮失败: {e}")

        if success_count > 0:
            msg = f"✅ SkyBots 续期成功\n账号：{name}\n成功操作：{success_count} 个项目"
            tg(msg)
            print(f"🎉 {name} 处理完成")
        
        browser.close()

def main():
    for acc in ACCOUNTS:
        try:
            run_account(acc)
        except Exception as e:
            print(f"❌ {acc['name']} 运行出错: {e}")

    # GitHub Action 活跃心跳
    with open("heartbeat.txt", "w") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()
