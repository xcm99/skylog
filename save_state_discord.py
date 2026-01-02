from playwright.sync_api import sync_playwright

LOGIN_URL = "https://dash.skybots.tech/fr/login"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    page.goto(LOGIN_URL)

    print("👉 请手动点击 Discord 登录并完成授权")
    print("👉 登录成功进入 Dashboard 后脚本会自动继续")

    page.wait_for_url("**/dashboard/**", timeout=0)

    context.storage_state(path="storage_state.json")
    print("✅ Discord Cookie 已保存：storage_state.json")

    browser.close()
