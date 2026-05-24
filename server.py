"""
KX自动查课 v17 — v15逻辑 + 浏览器自动恢复
"""
import sys,io,json,os,datetime as _dt,http.server,threading,requests
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding='utf-8')
from playwright.sync_api import sync_playwright

KX_U="16689655710"; KX_P="liguiteng1223"
LOG_PATH="C:/Users/Administrator/Desktop/server_debug.log"
def log(msg):
    try:
        with open(LOG_PATH,"a",encoding="utf-8") as f:
            f.write(f"[{_dt.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except:pass

_p=None; _b=None; _pg=None; _lock=threading.Lock(); _last=None
CID_MAP={"U校园AI版":7012,"U校园":7001,"学习通":6721,"智慧树":15755,"中国大学MOOC":11202,"清华社英语":7024,"长江雨课堂":14311}

PLATFORM_MAP={
    "U校园AI版":"PUP-U校园AI版","U校园":"PUP-U校园 整本","学习通":"恐龙学习通",
    "智慧树":"毛豆-智慧树/知到","中国大学MOOC":"恐龙中国大学MOOC",
    "清华社英语":"PUP-清华社英语","长江雨课堂":"恐龙-长江雨课堂",
}

def place_order(platform, account, password, courses_to_select):
    """在kx平台下单：查课→勾选→下单"""
    global _pg
    log(f"ORDER {platform} {len(courses_to_select)}门课")

    cid=CID_MAP.get(platform,7012)
    # 导航到add2
    if 'add2' not in _pg.url:
        _pg.goto("https://kx.nopoliceman.help/add2",wait_until="domcontentloaded")
        _pg.wait_for_timeout(2000)
    dismiss()

    # 我的收藏+选课
    _pg.locator('#collect').first.click(force=True)
    _pg.wait_for_timeout(3000)
    for _ in range(5):
        try:_pg.keyboard.press("Escape");_pg.wait_for_timeout(100)
        except:pass

    search_kw=PLATFORM_MAP.get(platform,platform[:4])
    _pg.evaluate("()=>{const s=document.querySelector('select');if(s&&$(s).data('select2'))$(s).select2('open');}")
    _pg.wait_for_timeout(2000)
    si=_pg.locator('input.select2-search__field')
    if si.count()>0:si.fill(search_kw)
    _pg.wait_for_timeout(3000)
    _pg.evaluate("()=>{const o=document.querySelector('.select2-results__option');if(o&&o.offsetParent){o.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));o.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));o.click();}}")
    _pg.wait_for_timeout(2000)
    _pg.evaluate("()=>{try{const s=document.querySelector('select');if(s&&$(s).data('select2'))$(s).select2('close');}catch(e){}}")
    _pg.wait_for_timeout(500)

    # 填表+查询
    for _ in range(3):
        try:_pg.keyboard.press("Escape");_pg.wait_for_timeout(100)
        except:pass
    ta=_pg.locator('textarea[placeholder*="下单格式"]')
    if ta.count()>0:ta.fill(f" {account} {password}",force=True)
    _pg.wait_for_timeout(500)
    _pg.locator('a:has-text("查询课程")').first.click(force=True)
    _pg.wait_for_timeout(8000)

    # 尝试勾选匹配的课程
    if courses_to_select and len(courses_to_select)>0:
        result=_pg.evaluate(f"""(courses)=>{{
            const checkboxes=document.querySelectorAll('input[type=checkbox]:visible');
            let matched=0;
            checkboxes.forEach(cb=>{{
                const row=cb.closest('tr,div,.check-item')?.textContent||'';
                for(const cn of courses){{
                    if(row.includes(cn.substring(0,6))||cn.includes(row.substring(0,10))){{
                        if(!cb.checked){{cb.click();matched++;}}
                        break;
                    }}
                }}
            }});
            return matched;
        }}""",courses_to_select)
        log(f"勾选{result}门")
        _pg.wait_for_timeout(1000)

    # 点"确认下单"或"我选好了"
    for btn_text in ['确认下单','我选好了','提交']:
        btn=_pg.locator(f'button:has-text("{btn_text}"):visible, a:has-text("{btn_text}"):visible').first
        if btn.count()>0:
            btn.click(force=True)
            log(f"点击:{btn_text}")
            _pg.wait_for_timeout(5000)
            break

    log("下单完成")
    return {'success':True,'msg':'下单请求已提交，请到kx平台确认订单状态'}

def init_browser():
    global _p,_b,_pg
    try:
        if _pg:_pg.evaluate("1");return
    except:pass
    log("启动浏览器...")
    try:
        if _b:_b.close()
        if _p:_p.stop()
    except:pass
    _p=sync_playwright().start()
    _b=_p.chromium.launch(headless=False,slow_mo=400)
    _pg=_b.new_page()
    _pg.set_default_timeout(15000)
    _pg.goto("https://kx.nopoliceman.help/home",wait_until="domcontentloaded")
    _pg.wait_for_timeout(3000)
    if 'login' in _pg.url:
        _pg.locator('input[placeholder*="账号"]').first.fill(KX_U)
        _pg.locator('input[placeholder*="密码"]').first.fill(KX_P)
        _pg.locator("#kt_sign_in_submit").first.click()
        _pg.wait_for_url("**/home",timeout=10000)
    log("就绪")

def dismiss():
    for _ in range(10):
        try:_pg.keyboard.press("Escape");_pg.wait_for_timeout(100)
        except:pass
    for t in ["关闭","取消","×","今日不再显示","今日不再提示"]:
        btns=_pg.locator(f'button:has-text("{t}")')
        for i in range(btns.count()):
            try:btns.nth(i).click(force=True,timeout=1000)
            except:pass
    for mid in ['modal_recommend','modal_tcgonggao']:
        try:
            b=_pg.locator(f'#{mid} .btn-close, #{mid} button:has-text("关闭")').first
            if b.count()>0:b.click(force=True,timeout=2000)
        except:pass

def do_check(platform, account, password):
    global _pg, _last
    log(f"CHECK {platform} {account}")
    same=(platform==_last)

    api_result=[]
    def on_resp(resp):
        try:
            if 'checkcourses/get' in resp.url and 'getclass' not in resp.url and 'getcate' not in resp.url:
                api_result.append(resp.json())
        except:pass
    _pg.on('response',on_resp)

    try:
        if not same:
            if 'add2' not in _pg.url:
                _pg.goto("https://kx.nopoliceman.help/add2",wait_until="domcontentloaded")
                _pg.wait_for_timeout(2000)
            dismiss()
            _pg.locator('#collect').first.click(force=True)
            _pg.wait_for_timeout(3000)
            for _ in range(5):
                try:_pg.keyboard.press("Escape");_pg.wait_for_timeout(100)
                except:pass
            kw=PLATFORM_MAP.get(platform,platform[:4])
            _pg.evaluate("()=>{const s=document.querySelector('select');if(s&&$(s).data('select2'))$(s).select2('open');}")
            _pg.wait_for_timeout(2000)
            si=_pg.locator('input.select2-search__field')
            if si.count()>0:si.fill(kw)
            _pg.wait_for_timeout(3000)
            _pg.evaluate("()=>{const o=document.querySelector('.select2-results__option');if(o&&o.offsetParent){o.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));o.dispatchEvent(new MouseEvent('mouseup',{bubbles:true}));o.click();}}")
            _pg.wait_for_timeout(2000)
            _pg.evaluate("()=>{try{const s=document.querySelector('select');if(s&&$(s).data('select2'))$(s).select2('close');}catch(e){}}")
            _pg.wait_for_timeout(500)
            _last=platform

        for _ in range(3):
            try:_pg.keyboard.press("Escape");_pg.wait_for_timeout(100)
            except:pass
        ta=_pg.locator('textarea[placeholder*="下单格式"]')
        if ta.count()>0:ta.fill(f" {account} {password}",force=True)
        _pg.wait_for_timeout(500)
        _pg.locator('a:has-text("查询课程")').first.click(force=True)
        _pg.wait_for_timeout(3000)

        # 兜底：requests直调
        if not api_result:
            log("兜底requests...")
            try:
                cks=_pg.context.cookies()
                s=requests.Session()
                s.headers.update({"User-Agent":"Mozilla/5.0","Content-Type":"application/json"})
                for c in cks:s.cookies.set(c['name'],c['value'])
                sel=_pg.evaluate("()=>{const s=document.querySelector('select');return s?s.value:'7012';}")
                r=s.post("https://kx.nopoliceman.help/api/v2/checkcourses/get",
                    json={"cid":int(sel),"userinfo":f"{account} {password}"},
                    headers={"Referer":"https://kx.nopoliceman.help/add2"})
                api_result.append(r.json())
            except Exception as e:log(f"兜底失败:{e}")

        for _ in range(10):
            try:_pg.wait_for_timeout(1000)
            except:break
            if api_result:break
    except Exception as e:
        log(f"交互异常:{e}, 标记需重建")
        _last=None
        init_browser()
        # 简单兜底
        cks=_pg.context.cookies()
        s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Content-Type":"application/json"})
        for c in cks:s.cookies.set(c['name'],c['value'])
        sel='7012'
        r=s.post("https://kx.nopoliceman.help/api/v2/checkcourses/get",
            json={"cid":int(sel),"userinfo":f"{account} {password}"},
            headers={"Referer":"https://kx.nopoliceman.help/add2"})
        api_result.append(r.json())

    log(f"API: {len(api_result)}")
    courses=[]
    for r in api_result:
        d=r.get('data',[])
        if isinstance(d,list):
            for c in d:courses.append(c.get('name',str(c)) if isinstance(c,dict) else str(c))
    if not courses:courses=['未查到课程，可能账号密码错误或无在读课程']
    log(f"结果: {len(courses)}门")
    return {'success':True,'courses':courses,'count':len(courses)}

# 价格存储（服务端统一管理，所有人看到一致价格）
_PRICES={
    "U校园AI版":4.51,"U校园":4.51,"学习通":2.90,"智慧树":3.90,
    "中国大学MOOC":1.98,"清华社英语":6.90,"长江雨课堂":3.90
}

class Handler(http.server.BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin','*')
        self.send_header('Access-Control-Allow-Methods','POST,GET,OPTIONS')
        self.send_header('Access-Control-Allow-Headers','Content-Type')
        self.end_headers()
    def do_GET(self):
        if self.path=='/api/prices':
            resp=json.dumps(_PRICES,ensure_ascii=False).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type','application/json;charset=utf-8')
            self.send_header('Access-Control-Allow-Origin','*')
            self.send_header('Content-Length',str(len(resp)))
            self.end_headers()
            self.wfile.write(resp)
        elif self.path in ('/','/index.html'):
            try:
                with open(r'C:\Users\Administrator\Desktop\网课代刷\index.html','r',encoding='utf-8') as f:
                    html=f.read()
                # 替换API地址为当前serveo地址
                resp=html.encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type','text/html;charset=utf-8')
                self.send_header('Access-Control-Allow-Origin','*')
                self.send_header('Content-Length',str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                self.send_response(500);self.end_headers()
        else:
            self.send_response(200)
            self.send_header('Content-Type','application/json')
            self.send_header('Access-Control-Allow-Origin','*')
            self.end_headers()
            self.wfile.write(json.dumps({'status':'ok'}).encode())
    def do_POST(self):
        if self.path=='/api/place-order':
            # 自动下单：查询→勾选课程→下单
            try:
                length=int(self.headers.get('Content-Length',0))
                body=self.rfile.read(length)
                try:data=json.loads(body)
                except:data=json.loads(body.decode('gbk'))
                account=data.get('account','');password=data.get('password','')
                platform=data.get('platform','');courses=data.get('courses',[])
                if not account or not password:
                    result={'success':False,'msg':'缺少账号密码'}
                else:
                    with _lock:init_browser()
                    result=place_order(platform,account,password,courses)
            except Exception as e:log(f"ORDER_ERR:{e}");result={'success':False,'msg':str(e)[:100]}
            resp=json.dumps(result,ensure_ascii=False).encode('utf-8')
            self.send_response(200);self.send_header('Content-Type','application/json;charset=utf-8')
            self.send_header('Access-Control-Allow-Origin','*');self.send_header('Content-Length',str(len(resp)))
            self.end_headers();self.wfile.write(resp)

        elif self.path=='/api/check-course':
            try:
                length=int(self.headers.get('Content-Length',0))
                body=self.rfile.read(length)
                try:data=json.loads(body)
                except:data=json.loads(body.decode('gbk'))
                account=data.get('account','').strip()
                password=data.get('password','').strip()
                platform=data.get('platform','')
                if not account or not password:result={'success':False,'error':'请填写账号和密码'}
                else:
                    with _lock:init_browser();result=do_check(platform,account,password)
            except Exception as e:log(f"ERR:{e}");result={'success':False,'error':str(e)[:100]}
            resp=json.dumps(result,ensure_ascii=False).encode('utf-8')
            self.send_response(200);self.send_header('Content-Type','application/json;charset=utf-8')
            self.send_header('Access-Control-Allow-Origin','*');self.send_header('Content-Length',str(len(resp)))
            self.end_headers();self.wfile.write(resp)
        elif self.path=='/api/prices':
            try:
                length=int(self.headers.get('Content-Length',0))
                body=self.rfile.read(length)
                data=json.loads(body)
                for k,v in data.items():
                    if k in _PRICES:_PRICES[k]=float(v)
                log(f"价格更新: {_PRICES}")
                resp=json.dumps({'success':True},ensure_ascii=False).encode('utf-8')
                self.send_response(200)
                self.send_header('Content-Type','application/json;charset=utf-8')
                self.send_header('Access-Control-Allow-Origin','*')
                self.send_header('Content-Length',str(len(resp)))
                self.end_headers()
                self.wfile.write(resp)
            except Exception as e:
                self.send_response(400);self.end_headers()
        else:self.send_response(404);self.end_headers()
    def log_message(self,f,*a):pass

if __name__=='__main__':
    log("SERVER v17")
    print("[SERVER] http://localhost:8800")
    http.server.HTTPServer(('127.0.0.1',8800),Handler).serve_forever()
