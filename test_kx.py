import asyncio, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        page = await browser.new_page()
        page.set_default_timeout(15000)

        print("1. 登录...")
        await page.goto("https://kx.nopoliceman.help/home", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        if 'login' in page.url:
            await page.locator('input[placeholder*="账号"]').first.fill('16689655710')
            await page.locator('input[placeholder*="密码"]').first.fill('liguiteng1223')
            await page.locator('#kt_sign_in_submit').first.click()
            await page.wait_for_url('**/home', timeout=10000)
            print("   登录成功!")

        print("2. 进入add2...")
        await page.goto("https://kx.nopoliceman.help/add2", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Dismiss any popup modals
        print("3. 关闭弹窗...")
        # Try clicking "关闭" button in modals
        for text in ['关闭', '×', '取消']:
            try:
                btn = page.locator(f'.modal button:has-text("{text}"):visible').first
                if await btn.count() > 0:
                    await btn.click()
                    print(f"   已关闭弹窗")
                    await page.wait_for_timeout(500)
                    break
            except:
                pass

        # Alternative: click outside modal or press Escape
        try:
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(300)
        except:
            pass

        # Find the textarea
        print("4. 填入账号信息...")
        ta = page.locator('textarea[placeholder*="下单"]').first
        await ta.fill("北京大学 test001 testpwd123")
        await page.wait_for_timeout(500)

        # Click "查课下单"
        print("5. 点击查课下单...")
        # Force click (bypasses overlays)
        btn = page.locator('button:has-text("查课下单"):visible').first
        if await btn.count() > 0:
            await btn.click(force=True)
            print("   已点击查课下单!")
        else:
            print("   没找到按钮")
            await page.screenshot(path=r"C:\Users\Administrator\Desktop\网课代刷\step_no_button.png")
            await browser.close()
            return

        await page.wait_for_timeout(5000)

        # Take screenshot of results
        await page.screenshot(path=r"C:\Users\Administrator\Desktop\网课代刷\step_after_check.png")
        print("6. 截图: step_after_check.png")

        # Check what happened - look for course results or error
        body = (await page.text_content('body') or '')[:2000]
        # Find relevant content
        for keyword in ['课程', '查询', '选择', '错误', '失败', '成功', '已选择', '查课']:
            if keyword in body:
                idx = body.find(keyword)
                snippet = body[max(0,idx-30):idx+80].replace('\n',' ')
                print(f"   [{keyword}]: {snippet}")

        print("\n7. 浏览器保持打开30秒查看结果...")
        await page.wait_for_timeout(30000)
        await browser.close()

asyncio.run(main())
