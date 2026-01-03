import base64
import json
import os
import time
import re
import requests  # 新增：用于发送截图文件
from playwright.sync_api import sync_playwright

# ========= 配置区 =========
TG_BOT = os.getenv("TG_BOT_TOKEN")
TG_CHAT = os.getenv("TG_CHAT_ID")
DASHBOARD = "https://dash.skybots.tech/fr/dashboard/my-projects"

ACCOUNTS = [
    {"name": "ACC1", "cookie": os.getenv("SKYBOTS_COOKIE_ACC1")},
]

def tg(msg, photo_path=None):
    """
    修改点 1：增强版推送函数
    支持发送纯文字或【图片+文字】
    """
    if not TG_BOT or not TG_CHAT:
        print(f"推送跳过：{msg}")
        return
    
    base_url = f"https://api.telegram.org/bot{TG_BOT}"
    try:
        if photo_path and os.path.exists(photo_path):
            # 发送图片接口
            with open(photo_path, 'rb') as f:
                requests.post(
                    f"{base_url}/sendPhoto",
                    data={"chat_id": TG_CHAT, "caption": msg},
                    files={"photo": f},
                    timeout=30
                )
        else:
            # 发送文字接口
            requests.post(
                f"{base_url}/sendMessage",
                json={"chat_id": TG_CHAT, "text": msg},
                timeout=15
            )
    except Exception as e:
        print(f"TG 发送失败: {e}")

def run_account(acc):
    name = acc["name"]
    if not acc["cookie"]:
        print(f"⚠️ 跳过 {name}：未配置环境变量")
        return

    try:
        state = json.loads(base64.b64decode(acc["cookie"]).decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Cookie 解码失败: {e}")

    with sync_playwright() as p:
        # 启动浏览器
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=state)
        page = context.new_page()

        print(f"🚀 正在处理账号: {name}...")
        
        # 增加等待，确保页面渲染完成
        page.goto(DASHBOARD, timeout=60_000, wait_until="networkidle")
        time.sleep(8) 

        # 1. 登录失效检查
        if "/login" in page.url:
            tg(f"⚠️ SkyBots 登录失效：{name}\n请重新获取 Cookie 并更新 Secret。")
            raise RuntimeError("Cookie 已过期")

        # 2. 查找续期按钮 (多语言兼容选择器)
        # 修改点 2：优化选择器，涵盖更多可能性
        renew_selector = "button:has-text('Renouveler'), button:has-text('Renew'), button:has-text('续期')"
        renew_buttons = page.locator(renew_selector)
        
        count = renew_buttons.count()
        
        # 修改点 3：如果没有找到按钮，执行截图并推送
        if count == 0:
            shot_name = f"debug_{name}.png"
            # 截取全屏，方便分析页面状态
            page.screenshot(path=shot_name, full_page=True) 
            print(f"ℹ️ {name}: 未发现按钮，已截屏记录")
            
            tg(f"ℹ️ 报告：账号 {name} 目前没有可续期的项目。\n请检查下方截图确认页面状态。", photo_path=shot_name)
            
            # 清理临时文件
            if os.path.exists(shot_name):
                os.remove(shot_name)
            return

        # 3. 如果找到了按钮，执行续期
        success_count = 0
        for i in range(count):
            btn = renew_buttons.nth(i)
            if btn.is_visible():
                try:
                    btn.scroll_into_view_if_needed()
                    btn.click()
                    time.sleep(5) # 点击后多等一会
                    success_count += 1
                except Exception as e:
                    print(f"点击失败: {e}")

        if success_count > 0:
            tg(f"✅ SkyBots 续期成功\n账号：{name}\n操作项目数：{success_count}")
        
        browser.close()

def main():
    for acc in ACCOUNTS:
        try:
            run_account(acc)
        except Exception as e:
            print(f"❌ {acc['name']} 报错: {e}")

    # GitHub Action 活跃心跳
    with open("heartbeat.txt", "w") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()
