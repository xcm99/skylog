import base64
import json
import os
import time
import re
import requests
from playwright.sync_api import sync_playwright

# ========= 配置区 =========
# 请确保在 GitHub Secrets 中配置了以下变量
TG_BOT = os.getenv("TG_BOT_TOKEN")
TG_CHAT = os.getenv("TG_CHAT_ID")

# 修正后的 URL：直接指向项目列表页，避免被重定向回首页
DASHBOARD = "https://dash.skybots.tech/dashboard/my-projects"

ACCOUNTS = [
    {"name": "ACC1", "cookie": os.getenv("SKYBOTS_COOKIE_ACC1")},
    # 如有更多账号，按此格式添加
]

def tg(msg, photo_path=None):
    """发送 Telegram 消息或图片"""
    if not TG_BOT or not TG_CHAT:
        print(f"未配置 TG 变量，跳过推送：{msg}")
        return
    
    base_url = f"https://api.telegram.org/bot{TG_BOT}"
    try:
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, 'rb') as f:
                requests.post(
                    f"{base_url}/sendPhoto",
                    data={"chat_id": TG_CHAT, "caption": msg},
                    files={"photo": f},
                    timeout=30
                )
        else:
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
        print(f"⚠️ 账号 {name} 未配置 Cookie，已跳过")
        return

    try:
        state = json.loads(base64.b64decode(acc["cookie"]).decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"Cookie 解码失败: {e}")

    with sync_playwright() as p:
        # 启动浏览器（Headless 模式适合 GitHub Actions）
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(storage_state=state)
        page = context.new_page()

        print(f"🚀 正在处理账号: {name}...")
        
        # 1. 访问项目列表页
        try:
            page.goto(DASHBOARD, timeout=60_000, wait_until="networkidle")
        except Exception:
            # 如果加载超时，尝试再次刷新
            page.reload(wait_until="networkidle")
        
        time.sleep(8)  # 等待异步组件加载

        # 2. 检查是否重定向到了登录页
        if "/login" in page.url:
            tg(f"⚠️ SkyBots 登录失效：{name}\nCookie 已过期，请重新获取并更新 Secret。")
            browser.close()
            return

        # 3. 强制校验页面：如果没进入项目页，尝试手动点击侧边栏
        if "my-projects" not in page.url:
            print("⚠️ 未能直接进入项目页，尝试点击侧边栏按钮...")
            # 尝试通过文本定位侧边栏菜单并点击
            project_link = page.get_by_role("link", name=re.compile(r"Mes Projets|My Projects", re.I))
            if project_link.count() > 0:
                project_link.click()
                time.sleep(5)

        # 4. 查找续期按钮 (多语言兼容：法/英/中)
        renew_selector = "button:has-text('Renouveler'), button:has-text('Renew'), button:has-text('续期')"
        renew_buttons = page.locator(renew_selector)
        
        count = renew_buttons.count()
        
        # 5. 如果没有找到按钮：截图并发送 TG 提醒
        if count == 0:
            shot_path = f"debug_{name}.png"
            page.screenshot(path=shot_path, full_page=True)
            print(f"ℹ️ {name}: 页面上未发现续期按钮")
            
            tg(f"ℹ️ 报告：账号 {name} 目前没有检测到可续期的项目。\n请查看截图确认状态。", photo_path=shot_path)
            
            if os.path.exists(shot_path):
                os.remove(shot_path)
            browser.close()
            return

        # 6. 如果找到了按钮：执行续期操作
        success_count = 0
        for i in range(count):
            btn = renew_buttons.nth(i)
            if btn.is_visible():
                try:
                    btn.scroll_into_view_if_needed()
                    btn.click()
                    time.sleep(5)  # 等待操作生效
                    success_count += 1
                except Exception as e:
                    print(f"按钮点击失败: {e}")

        if success_count > 0:
            tg(f"✅ SkyBots 续期成功\n账号：{name}\n成功执行：{success_count} 个项目")
            print(f"🎉 {name} 处理完成")
        
        browser.close()

def main():
    for acc in ACCOUNTS:
        try:
            run_account(acc)
        except Exception as e:
            print(f"❌ {acc['name']} 运行过程中出错: {e}")

    # GitHub Action 活跃心跳：更新本地文件以触发 Git 提交
    with open("heartbeat.txt", "w") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S"))

if __name__ == "__main__":
    main()
