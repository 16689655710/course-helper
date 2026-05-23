"""
KX平台自动查课下单脚本
用法: python kx_auto.py --school 北京大学 --account test001 --pass testpwd --script 超星学习通
      python kx_auto.py --order-id abc123  (从订单中读取信息)
"""
import asyncio, sys, io, json, os, argparse
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from playwright.async_api import async_playwright

KX_USER = "16689655710"
KX_PASS = "liguiteng1223"
ORDERS_FILE = r"C:\Users\Administrator\Desktop\网课代刷\pending_orders.json"

async def login(page):
    """登录kx平台"""
    await page.goto("https://kx.nopoliceman.help/home", wait_until="domcontentloaded")
    await page.wait_for_timeout(3000)
    if 'login' in page.url:
        await page.locator('input[placeholder*="账号"]').first.fill(KX_USER)
        await page.locator('input[placeholder*="密码"]').first.fill(KX_PASS)
        await page.locator('#kt_sign_in_submit').first.click()
        await page.wait_for_url('**/home', timeout=10000)
        print("✅ 登录成功")
    else:
        print("✅ 已登录")

async def dismiss_modal(page):
    """关闭弹窗"""
    for _ in range(3):
        try:
            for text in ['关闭', '×', '取消', '今日不再提示']:
                btn = page.locator(f'.modal button:has-text("{text}"):visible').first
                if await btn.count() > 0:
                    await btn.click(force=True)
                    await page.wait_for_timeout(300)
                    break
        except:
            pass
        try:
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(300)
        except:
            pass

async def select_script(page, script_name):
    """在add2页面选择课程脚本"""
    print(f"   查找脚本: {script_name}")

    # The page has a course list with clickable items
    # Try different selectors
    for sel in [
        f'a:has-text("{script_name}")',
        f'span:has-text("{script_name}")',
        f'div:has-text("{script_name}")',
        f'li:has-text("{script_name}")',
        f'tr:has-text("{script_name}")',
    ]:
        items = page.locator(sel)
        cnt = await items.count()
        if cnt > 0:
            # Click the first match
            for i in range(min(cnt, 5)):
                item = items.nth(i)
                txt = (await item.text_content() or '').strip()
                if script_name in txt and await item.is_visible():
                    await item.click(force=True)
                    await page.wait_for_timeout(2000)
                    print(f"   ✅ 已选择: {txt[:50]}")
                    return txt
    print(f"   ⚠️ 未找到脚本: {script_name}")
    return None

async def fill_account_info(page, school, account, password):
    """填入客户账号信息"""
    textarea = page.locator('textarea[placeholder*="下单"]').first
    if await textarea.count() == 0:
        textarea = page.locator('textarea').first
    combined = f"{school} {account} {password}"
    await textarea.fill(combined)
    print(f"   ✅ 已填入: {combined}")
    await page.wait_for_timeout(500)

async def click_check_course(page):
    """点击查课按钮"""
    for text in ['查课下单', '查询课程', '查课']:
        btn = page.locator(f'button:has-text("{text}"):visible').first
        if await btn.count() > 0:
            await btn.click(force=True)
            print(f"   ✅ 已点击: {text}")
            await page.wait_for_timeout(5000)
            return True
    return False

async def get_course_results(page):
    """获取查课结果"""
    body = (await page.text_content('body') or '')
    # Look for course list in modals or page content
    results = []

    # Check modal content first
    for modal_sel in ['.modal.show', '.modal.fade.show', '[role="dialog"]']:
        modal = page.locator(modal_sel).first
        if await modal.count() > 0 and await modal.is_visible():
            content = (await modal.text_content() or '')
            print(f"   弹窗内容: {content[:500]}")
            # Extract course names
            results = extract_courses(content)

    # Check page content
    if not results:
        results = extract_courses(body)

    return results

def extract_courses(text):
    """从文本中提取课程名称"""
    courses = []
    # Look for course name patterns
    for line in text.split('\n'):
        line = line.strip()
        if len(line) > 4 and len(line) < 200:
            # Filter out UI elements
            skip = ['系统导航', '学习管理', '用户中心', '后台首页', '消息通知',
                    '代理列表', '工单列表', '操作日志', '在线充值', '卡密充值',
                    '联系上级', '开通质押', '课程说明', '最新上架', '平台对接',
                    '插件下载', '更多菜单', '查课下单', '常用商品下单', '无查下单',
                    '订单列表', '可用项目', '课程分类', '课程名称', '重要通知',
                    'Good Morning', '退出登录', '清空缓存', '切换主题', '添加收藏']
            if any(s in line for s in skip):
                continue
            if any(c in line for c in ['（', '(', '元', '大学', 'MOOC', '智慧', '学习', '平台', '教育', '课程']):
                courses.append(line)
    return courses

async def select_courses_from_results(page, course_indices):
    """从查课结果中勾选课程"""
    checkboxes = page.locator('input[type="checkbox"]:visible')
    cnt = await checkboxes.count()
    print(f"   找到 {cnt} 个复选框")
    for idx in course_indices:
        if idx < cnt:
            cb = checkboxes.nth(idx)
            await cb.check()
            print(f"   ✅ 已勾选第 {idx+1} 项")

async def submit_order(page):
    """提交订单"""
    for text in ['提交', '下单', '确认']:
        btn = page.locator(f'button:has-text("{text}"):visible').first
        if await btn.count() > 0:
            await btn.click(force=True)
            print(f"   ✅ 已点击: {text}")
            await page.wait_for_timeout(3000)
            return True
    return False

# ═══════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════
async def run_check_order(school, account, password, script_name=None):
    """执行完整的查课下单流程"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=200)
        page = await browser.new_page()
        page.set_default_timeout(15000)

        print("=" * 50)
        print(f"学校: {school}  账号: {account}")
        print(f"脚本: {script_name or '自动选择'}")
        print("=" * 50)

        # 1. Login
        print("\n1️⃣ 登录...")
        await login(page)

        # 2. Go to add2
        print("2️⃣ 进入查课页面...")
        await page.goto("https://kx.nopoliceman.help/add2", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # 3. Dismiss modals
        await dismiss_modal(page)

        # 4. Select script if specified
        if script_name:
            print(f"3️⃣ 选择脚本: {script_name}")
            await select_script(page, script_name)

        # 5. Fill account info
        print("4️⃣ 填入客户信息...")
        await fill_account_info(page, school, account, password)

        # 6. Click check
        print("5️⃣ 查课...")
        await click_check_course(page)

        # Take screenshot
        await page.screenshot(path=r"C:\Users\Administrator\Desktop\网课代刷\auto_result.png")
        print("   📸 截图: auto_result.png")

        # 7. Get results
        print("6️⃣ 获取查课结果...")
        courses = await get_course_results(page)

        if courses:
            print(f"\n  查到 {len(courses)} 门课程:")
            for i, c in enumerate(courses[:20]):
                print(f"   [{i+1}] {c[:80]}")
        else:
            print("   ⚠️ 未提取到课程列表，请查看浏览器窗口")

        # Keep browser open
        print("\n浏览器保持打开，手动操作后关闭...")
        await page.wait_for_timeout(60000)
        await browser.close()

def process_pending_orders():
    """处理待处理订单"""
    if not os.path.exists(ORDERS_FILE):
        print(f"订单文件不存在: {ORDERS_FILE}")
        return

    with open(ORDERS_FILE, 'r', encoding='utf-8') as f:
        orders = json.load(f)

    pending = [o for o in orders if o.get('status') == 'pending']
    if not pending:
        print("没有待处理订单")
        return

    print(f"找到 {len(pending)} 个待处理订单\n")
    for i, o in enumerate(pending):
        print(f"[{i+1}] {o.get('course','?')} | {o.get('school','?')} | {o.get('account','?')} | ¥{o.get('total',0)}")

    try:
        choice = input(f"\n选择要处理的订单 (1-{len(pending)}, 或输入 q 退出): ").strip()
        if choice.lower() == 'q':
            return
        idx = int(choice) - 1
        if 0 <= idx < len(pending):
            order = pending[idx]
            asyncio.run(run_check_order(
                school=order.get('school', ''),
                account=order.get('account', ''),
                password=order.get('password', ''),
                script_name=order.get('course', None)
            ))
    except (ValueError, IndexError):
        print("无效输入")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='KX自动查课下单')
    parser.add_argument('--school', default='北京大学')
    parser.add_argument('--account', default='test001', help='客户账号')
    parser.add_argument('--pass', dest='password', default='testpwd', help='客户密码')
    parser.add_argument('--script', default=None, help='课程脚本名称')
    parser.add_argument('--order-id', default=None, help='从订单ID读取')
    parser.add_argument('--batch', action='store_true', help='批量处理待处理订单')

    args = parser.parse_args()

    if args.batch:
        process_pending_orders()
    else:
        asyncio.run(run_check_order(
            school=args.school,
            account=args.account,
            password=args.password,
            script_name=args.script
        ))
