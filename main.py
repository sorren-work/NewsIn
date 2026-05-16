import os, sys, traceback

# Global error logging for Android
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(_BASE_DIR, "error_log.txt")

if "ANDROID_ARGUMENT" in os.environ or "ANDROID_STORAGE" in os.environ:
    try:
        sys.stderr = open(LOG_FILE, "w")
        sys.stdout = sys.stderr
    except:
        pass

try:
    import pygame, news, ai, factcheck, weather as wx, auth
    try:
        import pyperclip
    except ImportError:
        pyperclip = None
    import re, json, threading, webbrowser, math, time
    from difflib import SequenceMatcher

    IS_ANDROID = "ANDROID_ARGUMENT" in os.environ or "ANDROID_STORAGE" in os.environ
    if IS_ANDROID:
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.INTERNET, Permission.WRITE_EXTERNAL_STORAGE, Permission.READ_EXTERNAL_STORAGE, Permission.RECORD_AUDIO])
            from android import show_keyboard, hide_keyboard
        except:
            def show_keyboard(): pass
            def hide_keyboard(): pass
            
        try:
            import certifi
            os.environ["SSL_CERT_FILE"] = certifi.where()
            os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()
        except:
            pass
    else:
        def show_keyboard(): pass
        def hide_keyboard(): pass
except Exception:
    if "ANDROID_ARGUMENT" in os.environ:
        with open(LOG_FILE, "a") as f:
            traceback.print_exc(file=f)
    raise

# Scaling and Dimensions
WIN_W, WIN_H = 1200, 720
if IS_ANDROID:
    pygame.display.init()
    info = pygame.display.Info()
    WIN_W, WIN_H = info.current_w, info.current_h
    # Scale based on a standard mobile width of 450px for better fit
    SCALE = WIN_W / 450.0
else:
    SCALE = 1.0

SIDEBAR_W   = int(238 * SCALE) if not IS_ANDROID else int(80 * SCALE)
CX          = SIDEBAR_W + int(10 * SCALE)
CW          = WIN_W - CX - int(10 * SCALE)
CARD_H      = int(128 * SCALE)
IMP_CARD_H  = int(136 * SCALE)
GAP         = int(8 * SCALE)
TOPBAR_H    = int(94 * SCALE)
TOPIC_BAR_H = int(30 * SCALE)
CONTENT_TOP = TOPBAR_H + TOPIC_BAR_H

# Path handling for Android
if IS_ANDROID:
    try:
        from android.storage import app_storage_path
        base_path = app_storage_path()
    except:
        base_path = "."
else:
    base_path = "."

SAVES_FILE    = os.path.join(base_path, "saved_news.json")
SETTINGS_FILE = os.path.join(base_path, "settings.json")
SESSION_FILE  = os.path.join(base_path, "session.json")
AUTO_RELOAD   = 300
LANG_CODES    = {"English":"en","Hindi":"hi","Nepali":"ne"}

pygame.init()
if IS_ANDROID:
    screen = pygame.display.set_mode((WIN_W, WIN_H), pygame.FULLSCREEN)
else:
    screen = pygame.display.set_mode((1200, 720), pygame.RESIZABLE)
pygame.display.set_caption("NewsIn")

def F(s, b=False):
    scaled_size = int(s * (SCALE if IS_ANDROID else 1.0))
    if not IS_ANDROID and s > 20: scaled_size = s # Don't overscale on desktop
    for fn in ["segoeui", "arial", "sans-serif", "dejavusans", "roboto"]:
        try:
            f = pygame.font.SysFont(fn, scaled_size, bold=b)
            if f: return f
        except: continue
    return pygame.font.SysFont(None, scaled_size, bold=b)

fH=F(24,True);fT=F(19,True);fB=F(16);fSm=F(13);fXs=F(12)
fTg=F(11,True);fBtn=F(13,True);fSrch=F(15)

DK=dict(bg=(13,17,23),sb=(20,25,32),sb2=(26,32,42),card=(20,25,32),
        tx=(220,228,236),sub=(100,114,130),bdr=(34,42,54),acc=(56,139,253),
        grn=(35,134,54),red=(200,50,50),org=(190,120,0),
        tag=(18,42,76),tagtx=(90,170,255),panel=(15,20,28),
        ton=(35,134,54),tof=(50,60,72),hbar=(16,20,27),
        dot=(38,48,62),doth=(56,139,253),ok=(18,55,28),oktx=(72,210,100),
        imp_bg=(18,28,16),imp_bdr=(35,100,45),srch_bg=(24,30,40),srch_bdr=(56,139,253))
LT=dict(bg=(245,247,250),sb=(255,255,255),sb2=(236,242,250),card=(255,255,255),
        tx=(14,20,28),sub=(88,100,116),bdr=(208,218,230),acc=(9,105,218),
        grn=(26,127,55),red=(185,28,28),org=(160,90,0),
        tag=(218,232,255),tagtx=(9,80,200),panel=(250,252,255),
        ton=(26,127,55),tof=(148,160,172),hbar=(240,245,252),
        dot=(208,218,230),doth=(9,105,218),ok=(218,242,220),oktx=(26,100,40),
        imp_bg=(238,250,240),imp_bdr=(80,180,80),srch_bg=(240,245,252),srch_bdr=(9,105,218))
dark=True
def C(): return DK if dark else LT

# ── State ──────────────────────────────────────────────────────────────────────
app_lang="Hindi"; ai.voice_lang="hi"
mode="global"; imp_arts=[]; nrm_arts=[]; err=None
gemini_api_key=""; set_active_input=None
home_country=None
page_scroll=0; panel=None; loading=False
dot_open=False; dot_idx=None; dot_section=None
saved=[]; sav_scroll=0
detail_open=False; detail_art=None
last_reload=time.time(); new_badge=False; new_badge_timer=0
notifs=[]

# Topic filters
TOPICS={
    "All":[],
    "Politics":["government","minister","president","parliament","election","vote","party","policy","senate","congress"],
    "War":["war","attack","military","airstrike","missile","troops","conflict","killed","bomb","battle","invasion","ceasefire","soldier","shoot"],
    "Economy":["economy","gdp","inflation","market","trade","bank","finance","currency","stock","recession","investment","tax","oil","price"],
    "Tech":["technology","ai","artificial intelligence","cyber","software","app","internet","robot","space","nasa","satellite","hack"],
    "Climate":["climate","flood","earthquake","storm","wildfire","drought","emissions","carbon","environment","disaster","hurricane","tsunami"],
    "Sports":["cricket","football","soccer","olympics","tournament","championship","match","player","team","fifa","ipl","nba","world cup"],
    "Health":["health","disease","vaccine","hospital","doctor","virus","cancer","medicine","covid","outbreak","treatment","surgery"],
}
active_topic="All"

def topic_match(art):
    """Match topic keywords as **words/phrases**, not arbitrary substrings (avoids e.g. 'war' in 'award')."""
    if active_topic=="All":
        return True
    blob = (gv(art, "title", "") + " " + gv(art, "summary", "")).strip()
    if not blob:
        return False
    low = blob.lower()
    for k in TOPICS[active_topic]:
        kw = k.strip().lower()
        if not kw:
            continue
        if " " in kw:
            pat = r"\s+".join(re.escape(w) for w in kw.split())
            if re.search(pat, low):
                return True
        else:
            if len(kw) <= 2:
                pat = r"(?<![a-z0-9])" + re.escape(kw) + r"(?![a-z0-9])"
            else:
                pat = r"\b" + re.escape(kw) + r"\b"
            if re.search(pat, low, re.I):
                return True
    return False

# Search
search_query=""; search_results=[]; search_active=False
search_sel_s=None; search_sel_e=None; mouse_on_search=False

# Weather
wx_panel_open=False; wx_country=None; wx_city=None
wx_data=None; wx_loading=False
wx_c_scroll=0; wx_city_scroll=0
wx_c_query=""; wx_city_query=""; wx_active_input=None
wx_c_search_rect=None; wx_city_search_rect=None
_wx_country_col_rect=None
_wx_city_col_rect=None
_wx_country_col_hit=None
_wx_city_col_hit=None
_wx_vis_c=13
_wx_vis_city=10
_wx_city_row_count=0
wx_last_mp=(0,0)

# Rects
_crects=[]; _drects=[]
_dot_st=None; _set_r=None; _detail_r=None
_detail_sel_full=""
_detail_line_spans=None  # list of (rect, g0, g1, line_text, font)  g0:g1 slice into _detail_sel_full
_detail_sel_a=_detail_sel_b=None
_detail_text_drag=False
_news_line_hits=[]  # card line hit-zones for drag-copy
_news_line_drag=False
_news_line_hit=None
_news_sel_ch0=_news_sel_ch1=None
_sav_r=[]; _sdel_r=[]
_topic_rects=[]; _wx_c_rects=[]; _wx_city_rects=[]
reload_rect=None; search_rect=None; search_clear_r=None
_cursor_blink=0

# ── Login / Register screen ───────────────────────────────────────────────────
_auth_mode = "login"  # "login" or "register"
_auth_email = ""
_auth_pass = ""
_auth_msg = ""
_auth_msg_clr = None
_auth_focus = "email"  # "email" or "pass"
_auth_loading = False

def draw_auth_screen(surf):
    c=C()
    surf.fill(c["bg"])
    pw=420; ph=380; px=(WIN_W-pw)//2; py=(WIN_H-ph)//2
    R(surf,c["panel"],(px,py,pw,ph),16)
    pygame.draw.rect(surf,c["bdr"],(px,py,pw,ph),width=1,border_radius=16)
    # Title
    title = "Welcome to NewsIn"
    surf.blit(fH.render(title,True,c["acc"]),(px+pw//2-fH.size(title)[0]//2,py+18))
    sub = "Login" if _auth_mode=="login" else "Create Account"
    surf.blit(fT.render(sub,True,c["tx"]),(px+pw//2-fT.size(sub)[0]//2,py+52))
    # Email field
    surf.blit(fSm.render("Email",True,c["sub"]),(px+30,py+90))
    email_r=pygame.Rect(px+30,py+108,pw-60,34)
    R(surf,c["sb2"],email_r,8)
    bc=c["acc"] if _auth_focus=="email" else c["bdr"]
    pygame.draw.rect(surf,bc,email_r,width=1,border_radius=8)
    et=_auth_email if _auth_email else "Enter email..."
    ec=c["tx"] if _auth_email else c["sub"]
    surf.blit(fB.render(clamp(et,fB,pw-80),True,ec),(email_r.x+10,email_r.y+7))
    # Blinking cursor for email
    if _auth_focus=="email" and int(time.time()*2)%2==0:
        cx_pos=email_r.x+10+fB.size(_auth_email)[0]
        pygame.draw.line(surf,c["tx"],(cx_pos,email_r.y+6),(cx_pos,email_r.y+28),1)
    # Password field
    surf.blit(fSm.render("Password",True,c["sub"]),(px+30,py+155))
    pass_r=pygame.Rect(px+30,py+173,pw-60,34)
    R(surf,c["sb2"],pass_r,8)
    bc2=c["acc"] if _auth_focus=="pass" else c["bdr"]
    pygame.draw.rect(surf,bc2,pass_r,width=1,border_radius=8)
    pt="•"*len(_auth_pass) if _auth_pass else "Enter password..."
    pc=c["tx"] if _auth_pass else c["sub"]
    surf.blit(fB.render(clamp(pt,fB,pw-80),True,pc),(pass_r.x+10,pass_r.y+7))
    # Blinking cursor for password
    if _auth_focus=="pass" and int(time.time()*2)%2==0:
        cx_pos=pass_r.x+10+fB.size("•"*len(_auth_pass))[0]
        pygame.draw.line(surf,c["tx"],(cx_pos,pass_r.y+6),(cx_pos,pass_r.y+28),1)
    # Submit button
    btn_text = "Login" if _auth_mode=="login" else "Register"
    btn_r=pygame.Rect(px+30,py+225,pw-60,40)
    R(surf,c["acc"],btn_r,10)
    surf.blit(fBtn.render(btn_text,True,(255,255,255)),(btn_r.x+(pw-60-fBtn.size(btn_text)[0])//2,btn_r.y+10))
    # Toggle link
    if _auth_mode=="login":
        tog_text="Don't have an account? Register"
    else:
        tog_text="Already have an account? Login"
    tog_r=pygame.Rect(px+30,py+275,pw-60,24)
    surf.blit(fSm.render(tog_text,True,c["acc"]),(px+pw//2-fSm.size(tog_text)[0]//2,py+278))
    # Message
    if _auth_msg:
        mc=_auth_msg_clr or c["red"]
        # Wrap message if too long
        msg_lines=wrap(_auth_msg,fSm,pw-60)
        for i,ml in enumerate(msg_lines[:2]):
            surf.blit(fSm.render(ml,True,mc),(px+30,py+310+i*16))
    # Loading
    if _auth_loading:
        surf.blit(fSm.render("Please wait...",True,c["sub"]),(px+pw//2-40,py+ph-30))
    pygame.display.flip()
    return email_r, pass_r, btn_r, tog_r

# ── Country picker (shown after first login) ──────────────────────────────────
def draw_country_picker(surf, selected_country, c_scroll, c_query):
    c=C()
    surf.fill(c["bg"])
    pw=500; ph=440; px=(WIN_W-pw)//2; py=(WIN_H-ph)//2
    R(surf,c["panel"],(px,py,pw,ph),16)
    pygame.draw.rect(surf,c["bdr"],(px,py,pw,ph),width=1,border_radius=16)
    surf.blit(fH.render("Select Your Home Country",True,c["acc"]),(px+pw//2-fH.size("Select Your Home Country")[0]//2,py+16))
    surf.blit(fSm.render("This will filter weather to your local cities.",True,c["sub"]),(px+28,py+48))
    # Search box
    sr=pygame.Rect(px+28,py+72,pw-56,30)
    R(surf,c["sb2"],sr,8)
    pygame.draw.rect(surf,c["bdr"],sr,width=1,border_radius=8)
    sq=c_query if c_query else "Search country..."
    sqc=c["tx"] if c_query else c["sub"]
    surf.blit(fSm.render(sq,True,sqc),(sr.x+10,sr.y+6))
    # Blinking cursor for country search
    if int(time.time()*2)%2==0:
        # If query is empty, cursor at start. If not, at end of text.
        txt_w = fSm.size(c_query)[0] if c_query else 0
        cx_pos=sr.x+10+txt_w
        pygame.draw.line(surf,c["tx"],(cx_pos,sr.y+6),(cx_pos,sr.y+24),1)
    # Country list
    countries=wx.COUNTRY_NAMES
    if c_query:
        countries=[cn for cn in countries if c_query.lower() in cn.lower()]
    vis=10
    rects=[]
    for i in range(c_scroll, min(c_scroll+vis, len(countries))):
        cn=countries[i]
        cr=pygame.Rect(px+28,py+110+(i-c_scroll)*30,pw-56,28)
        on=(cn==selected_country)
        R(surf,c["acc"] if on else c["sb2"],cr,6)
        if not on: pygame.draw.rect(surf,c["bdr"],cr,width=1,border_radius=6)
        surf.blit(fSm.render(cn,True,(255,255,255) if on else c["tx"]),(cr.x+12,cr.y+5))
        rects.append((cn,cr))
    # Confirm button
    btn_r=pygame.Rect(px+pw//2-80,py+ph-54,160,40)
    can_confirm=selected_country is not None
    R(surf,c["grn"] if can_confirm else c["sb2"],btn_r,10)
    surf.blit(fBtn.render("Continue →",True,(255,255,255) if can_confirm else c["sub"]),(btn_r.x+30,btn_r.y+10))
    pygame.display.flip()
    return rects, btn_r, sr, countries

# ── Language picker (shown on startup) ────────────────────────────────────────
lang_chosen=False

def draw_lang_picker(surf):
    c=C()
    surf.fill(c["bg"])
    ov=pygame.Surface((WIN_W,WIN_H),pygame.SRCALPHA); ov.fill((0,0,0,200)); surf.blit(ov,(0,0))
    pw=460; ph=280; px=(WIN_W-pw)//2; py=(WIN_H-ph)//2
    R(surf,c["panel"],(px,py,pw,ph),16)
    pygame.draw.rect(surf,c["bdr"],(px,py,pw,ph),width=1,border_radius=16)
    surf.blit(fH.render("Welcome to NewsIn",True,c["acc"]),(px+pw//2-fH.size("Welcome to NewsIn")[0]//2,py+20))
    surf.blit(fB.render("Choose your preferred language for voice:",True,c["tx"]),(px+24,py+66))
    surf.blit(fXs.render("You can change this later in Settings.",True,c["sub"]),(px+24,py+92))
    rects=[]
    for i,(lang,code) in enumerate(LANG_CODES.items()):
        r=pygame.Rect(px+24+i*140,py+130,128,48)
        on=(lang==app_lang)
        R(surf,c["acc"] if on else c["sb2"],r,12)
        if not on: pygame.draw.rect(surf,c["bdr"],r,width=1,border_radius=12)
        ls=fT.render(lang,True,(255,255,255) if on else c["tx"])
        surf.blit(ls,(r.x+(128-ls.get_width())//2,r.y+(48-ls.get_height())//2))
        rects.append((lang,r))
    # Confirm button
    cr=pygame.Rect(px+pw//2-80,py+ph-64,160,42)
    R(surf,c["grn"],cr,10)
    surf.blit(fBtn.render("Start App  →",True,(255,255,255)),(cr.x+(160-fBtn.size("Start App  →")[0])//2,cr.y+12))
    pygame.display.flip()
    return rects, cr

# ── Helpers ────────────────────────────────────────────────────────────────────
def R(s,c,r,rad=8): pygame.draw.rect(s,c,r,border_radius=rad)
def pill(s,c,r): pygame.draw.rect(s,c,r,border_radius=r.height//2)

def wrap(txt,fnt,maxw):
    words=txt.split(); lines=[]; ln=""
    for w in words:
        t=ln+w+" "
        if fnt.size(t)[0]<maxw: ln=t
        else: lines.append(ln.rstrip()); ln=w+" "
    if ln: lines.append(ln.rstrip())
    return lines

def clamp(txt,fnt,maxw):
    if fnt.size(txt)[0]<=maxw: return txt
    while txt and fnt.size(txt+"…")[0]>maxw: txt=txt[:-1]
    return txt+"…"

def gv(a,k,d=""):
    if isinstance(a,dict): return a.get(k,d) or d
    return getattr(a,k,d) or d

def gtitle(a): return gv(a,"title","No title")
def gsrc(a):   return str(gv(a,"source",""))
def glink(a):  return gv(a,"link","")
def gsum(a):   return gv(a,"summary","")
def gimg(a):   return gv(a,"image","")
def gvid(a):   return gv(a,"video","")
def gsrcs(a):  return a.get("sources",[]) if isinstance(a,dict) else []
def gver(a):   return a.get("verified",False) if isinstance(a,dict) else False
def gimp(a):   return a.get("important",False) if isinstance(a,dict) else False
def gsc(a):    return a.get("source_count",1) if isinstance(a,dict) else 1
def gage(a):   return a.get("age_hours") if isinstance(a,dict) else None

def age_lbl(a):
    h=gage(a)
    if h is None: return ""
    if h<1: return f"{int(h*60)}m ago"
    if h<24: return f"{int(h)}h ago"
    return f"{int(h//24)}d ago"

def push_notif(msg):
    notifs.append({"msg":msg,"timer":240})

def do_search(q):
    global search_results
    if not q.strip(): search_results=[]; return
    all_arts=imp_arts+nrm_arts+saved; out=[]
    for art in all_arts:
        title=gtitle(art)
        words=[w for w in q.lower().split() if len(w)>2]
        wm=sum(1 for w in words if w in title.lower())/max(len(words),1) if words else 0
        score=max(SequenceMatcher(None,q.lower(),title.lower()).ratio(),wm*0.75)
        if score>=0.28: out.append((score,art))
    out.sort(key=lambda x:x[0],reverse=True)
    search_results=[a for _,a in out[:15]]

def char_at_x(mx):
    base=CX+36
    for i in range(len(search_query)+1):
        if base+fSrch.size(search_query[:i])[0]>=mx: return i
    return len(search_query)

def get_sel():
    if search_sel_s is None or search_sel_e is None: return ""
    a,b=sorted([search_sel_s,search_sel_e])
    return search_query[a:b]

def _char_at_x_in_line(font, line, x_local):
    if x_local <= 0:
        return 0
    for i in range(len(line) + 1):
        if font.size(line[:i])[0] >= x_local:
            return i
    return len(line)

def _detail_sel_index_at(mx, my):
    if not _detail_line_spans:
        return None
    for r, g0, g1, ln, fnt in _detail_line_spans:
        if r.collidepoint(mx, my):
            return min(g0 + _char_at_x_in_line(fnt, ln, mx - r.x), g1)
    return None

def _blit_sel_band(surf, x, y, w, h):
    if w < 1:
        return
    h = max(1, h)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    s.fill((56, 100, 200, 100))
    surf.blit(s, (x, y))

# ── Persistence ────────────────────────────────────────────────────────────────
def load_settings():
    global gemini_api_key
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE,"r",encoding="utf-8") as f: 
                d=json.load(f)
                gemini_api_key=d.get("gemini_api_key","")
        except: pass
    import factcheck
    factcheck.API_KEY = gemini_api_key

def save_settings():
    try:
        with open(SETTINGS_FILE,"w",encoding="utf-8") as f: 
            json.dump({"gemini_api_key":gemini_api_key},f)
    except: pass
    import factcheck
    factcheck.API_KEY = gemini_api_key

def load_saved():
    global saved
    if os.path.exists(SAVES_FILE):
        try:
            with open(SAVES_FILE,"r",encoding="utf-8") as f: saved=json.load(f)
        except: saved=[]

def write_saved():
    try:
        with open(SAVES_FILE,"w",encoding="utf-8") as f: json.dump(saved,f,ensure_ascii=False,indent=2)
    except: pass
    if auth.is_logged_in(): auth.cloud_save_news_async(saved)

def do_save(art):
    e={"title":gtitle(art),"source":gsrc(art),"link":glink(art),"summary":gsum(art),
       "image":gimg(art),"video":gvid(art),"sources":gsrcs(art),"verified":gver(art),
       "important":gimp(art),"source_count":gsc(art)}
    if not any(s["title"]==e["title"] for s in saved):
        saved.insert(0,e); write_saved(); push_notif(f"Saved: {gtitle(art)[:45]}")

def rm_saved(i):
    if 0<=i<len(saved): saved.pop(i); write_saved()

def share_article(art):
    t=gtitle(art); lnk=glink(art); src=gsrc(art)
    txt=f"📰 {t}"
    if src: txt+=f"\nSource: {src}"
    if lnk: txt+=f"\nRead: {lnk}"
    try: copy_to_clipboard(txt); push_notif("Copied! Paste to share on WhatsApp/Telegram.")
    except: push_notif("Could not copy.")

# ── Load news ──────────────────────────────────────────────────────────────────
def load_news(m, force=False):
    global imp_arts,nrm_arts,err,mode,page_scroll,loading,last_reload,new_badge,new_badge_timer
    mode=m; page_scroll=0; loading=True
    def _run():
        global imp_arts,nrm_arts,err,loading,last_reload,new_badge,new_badge_timer
        if force: news.clear_cache(m)
        fn=news.get_global_news if m=="global" else news.get_india_news
        i,n,e,is_new=fn()
        imp_arts=i; nrm_arts=n; err=e; loading=False
        last_reload=time.time()
        if is_new:
            new_badge=True; new_badge_timer=200
            if force: push_notif(f"Loaded {len(i)} important + {len(n)} latest stories!")
    threading.Thread(target=_run,daemon=True).start()

def auto_reload_tick():
    global last_reload
    if not loading and time.time()-last_reload>AUTO_RELOAD:
        def _bg():
            global imp_arts,nrm_arts,new_badge,new_badge_timer
            fn=news.get_global_news if mode=="global" else news.get_india_news
            i,n,_,is_new=fn()
            if is_new: imp_arts=i; nrm_arts=n; new_badge=True; new_badge_timer=200; push_notif("News updated!")
        threading.Thread(target=_bg,daemon=True).start()
        last_reload=time.time()

def filtered(arts): return [a for a in arts if topic_match(a)]

# ── Icons ──────────────────────────────────────────────────────────────────────
def icon(surf,name,x,y,sz=18,col=(255,255,255)):
    c=x+sz//2; m=y+sz//2
    if name=="globe":
        pygame.draw.circle(surf,col,(c,m),sz//2-1,2)
        pygame.draw.line(surf,col,(c,y+1),(c,y+sz-2),1)
        pygame.draw.line(surf,col,(x+1,m),(x+sz-2,m),1)
        pygame.draw.ellipse(surf,col,(x+2,m-3,sz-4,6),1)
    elif name=="flag":
        pygame.draw.rect(surf,(255,153,51),(x,y,sz,sz//3))
        pygame.draw.rect(surf,(255,255,255),(x,y+sz//3,sz,sz//3))
        pygame.draw.rect(surf,(19,136,8),(x,y+2*sz//3,sz,sz//3))
        pygame.draw.circle(surf,(0,0,128),(c,m),3,1)
    elif name=="gear":
        pygame.draw.circle(surf,col,(c,m),4,2)
        for a in range(0,360,45):
            rad=math.radians(a)
            pygame.draw.line(surf,col,(c+int(4*math.cos(rad)),m+int(4*math.sin(rad))),
                             (c+int(8*math.cos(rad)),m+int(8*math.sin(rad))),2)
    elif name=="pin":
        pygame.draw.polygon(surf,col,[(c,y+1),(x+sz-3,y+8),(c+2,y+14),(c,y+sz-1),(c-2,y+14),(x+3,y+8)])
        pygame.draw.circle(surf,C()["sb"],(c,y+8),3)
    elif name=="dots":
        for dy in [y+4,y+9,y+14]: pygame.draw.circle(surf,col,(c,dy),2)
    elif name=="reload":
        pygame.draw.arc(surf,col,(x+2,y+2,sz-4,sz-4),math.radians(40),math.radians(320),2)
        pygame.draw.polygon(surf,col,[(x+sz-4,y+2),(x+sz-2,y+7),(x+sz-9,y+6)])
    elif name=="speak":
        pygame.draw.rect(surf,col,(c-3,y+2,6,9),border_radius=3)
        pygame.draw.arc(surf,col,(c-6,y+7,12,8),3.14,0,2)
        pygame.draw.line(surf,col,(c,y+15),(c,y+sz-1),2)
        pygame.draw.line(surf,col,(c-3,y+sz-1),(c+3,y+sz-1),2)
    elif name=="search":
        pygame.draw.circle(surf,col,(c-2,m-2),sz//2-4,2)
        pygame.draw.line(surf,col,(c+3,m+3),(x+sz-2,y+sz-2),2)
    elif name=="close":
        pygame.draw.line(surf,col,(x+3,y+3),(x+sz-3,y+sz-3),2)
        pygame.draw.line(surf,col,(x+sz-3,y+3),(x+3,y+sz-3),2)
    elif name=="weather":
        pygame.draw.circle(surf,col,(c-1,m),4)
        pygame.draw.arc(surf,col,(x+1,y+2,sz-2,sz-4),math.radians(0),math.radians(180),2)
        for ox in [-3,0,3]: pygame.draw.line(surf,col,(c+ox,m+4),(c+ox,m+8),1)
    elif name=="share":
        pygame.draw.circle(surf,col,(x+sz-4,y+4),3)
        pygame.draw.circle(surf,col,(x+4,m),3)
        pygame.draw.circle(surf,col,(x+sz-4,y+sz-4),3)
        pygame.draw.line(surf,col,(x+4,m),(x+sz-4,y+4),1)
        pygame.draw.line(surf,col,(x+4,m),(x+sz-4,y+sz-4),1)

SB=[("global","Global News","globe"),("india","India News","flag"),
    ("weather","Weather","weather"),("saved","Saved News","pin"),("settings","Settings","gear")]

# ── Notifications ──────────────────────────────────────────────────────────────
def draw_notifs(surf):
    c=C(); ny=WIN_H-44; alive=[]
    for n in notifs:
        n["timer"]-=1
        if n["timer"]>0:
            ns=pygame.Surface((420,30),pygame.SRCALPHA)
            pygame.draw.rect(ns,(22,32,48),ns.get_rect(),border_radius=8)
            pygame.draw.rect(ns,c["acc"],ns.get_rect(),width=1,border_radius=8)
            ns.set_alpha(min(255,n["timer"]*4))
            surf.blit(ns,(WIN_W-430,ny))
            surf.blit(fXs.render(clamp(n["msg"],fXs,400),True,c["tx"]),(WIN_W-426,ny+8))
            ny-=36; alive.append(n)
    notifs.clear(); notifs.extend(alive)

# ── Sidebar ────────────────────────────────────────────────────────────────────
def draw_sidebar(surf):
    c=C()
    R(surf,c["sb"],(0,0,SIDEBAR_W,WIN_H))
    pygame.draw.line(surf,c["bdr"],(SIDEBAR_W-1,0),(SIDEBAR_W-1,WIN_H),1)
    R(surf,c["hbar"],(0,0,SIDEBAR_W,50))
    surf.blit(fH.render("NewsIn",True,c["acc"]),(14,12))
    y=58
    for key,lbl,ico in SB:
        active=(key==mode and panel is None) or key==panel
        R(surf,c["sb2"] if active else c["sb"],(5,y,SIDEBAR_W-10,40),8)
        if active: R(surf,c["acc"],(5,y,3,40),2)
        icol=c["acc"] if active else c["sub"]
        icon(surf,ico,17,y+11,18,icol)
        surf.blit(fBtn.render(lbl,True,c["tx"] if active else c["sub"]),(42,y+12))
        y+=46
    pygame.draw.line(surf,c["bdr"],(12,y+2),(SIDEBAR_W-12,y+2),1); y+=12
    von=ai.voice.is_on
    vr=pygame.Rect(12,y,SIDEBAR_W-24,26)
    pill(surf,c["ton"] if von else c["tof"],vr)
    icon(surf,"speak",18,y+4,18,(255,255,255))
    surf.blit(fXs.render("Voice ON" if von else "Voice OFF",True,(255,255,255)),(40,y+6))
    y+=34
    surf.blit(fXs.render(f"Lang: {app_lang}",True,c["sub"]),(14,y))
    surf.blit(fXs.render("F5 reload · F8 voice · drag text=copy",True,c["sub"]),(8,WIN_H-32))
    surf.blit(fXs.render("3-dot > Speak / Save / Share",True,c["sub"]),(10,WIN_H-16))

# ── Topbar ─────────────────────────────────────────────────────────────────────
def draw_topbar(surf):
    global reload_rect,search_rect,search_clear_r,_cursor_blink
    c=C()
    R(surf,c["hbar"],(CX-8,0,WIN_W,TOPBAR_H))
    if panel=="weather":
        reload_rect=search_rect=search_clear_r=None
        surf.blit(fH.render("Weather",True,c["tx"]),(CX,26))
        surf.blit(fSm.render("Countries A–Z · cities under each · wheel on the column you want.", True, c["sub"]), (CX, 58))
        return
    mode_lbl="Global News" if mode=="global" else "India News"
    surf.blit(fH.render(mode_lbl,True,c["tx"]),(CX,8))
    global new_badge,new_badge_timer
    if new_badge:
        new_badge_timer-=1
        if new_badge_timer<=0: new_badge=False
        else: surf.blit(fTg.render("● NEW",True,(255,80,80)),(CX+fH.size(mode_lbl)[0]+10,14))
    bx=WIN_W-8; bx-=32
    reload_rect=pygame.Rect(bx,8,26,26)
    R(surf,c["sb2"],reload_rect,6); icon(surf,"reload",bx+4,12,18,c["acc"])
    # Search bar
    sx=CX; sy=38; sw=WIN_W-CX-48; sh=30
    search_rect=pygame.Rect(sx,sy,sw,sh)
    R(surf,c["srch_bg"],search_rect,8)
    pygame.draw.rect(surf,c["srch_bdr"] if search_active else c["bdr"],search_rect,width=2,border_radius=8)
    icon(surf,"search",sx+8,sy+6,18,c["sub"])
    disp=search_query
    # Selection highlight
    if search_active and search_sel_s is not None and search_sel_e is not None:
        a,b=sorted([search_sel_s,search_sel_e])
        if a!=b:
            x0=sx+32+fSrch.size(disp[:a])[0]; x1=sx+32+fSrch.size(disp[:b])[0]
            ss=pygame.Surface((x1-x0,sh-8),pygame.SRCALPHA); ss.fill((56,100,200,130))
            surf.blit(ss,(x0,sy+4))
    surf.blit(fSrch.render(disp or "Search news by title…",True,c["tx"] if disp else c["sub"]),(sx+32,sy+6))
    if search_active:
        _cursor_blink=(_cursor_blink+1)%50
        if _cursor_blink<25:
            cp=search_sel_e if (search_sel_e is not None and disp) else (len(disp) if disp else 0)
            cx2=sx+32+fSrch.size(disp[:cp])[0]+1
            pygame.draw.line(surf,c["tx"],(cx2,sy+5),(cx2,sy+sh-5),2)
    search_clear_r=None
    if disp:
        xr=pygame.Rect(sx+sw-26,sy+4,22,22)
        R(surf,c["bdr"],xr,6); icon(surf,"close",xr.x+3,xr.y+3,16,c["sub"])
        search_clear_r=xr

# ── Topic bar — only on news panels ────────────────────────────────────────────
def draw_topic_bar(surf):
    global _topic_rects
    if panel in("saved","weather"): return
    c=C(); _topic_rects=[]; bx=CX; by=TOPBAR_H+4; bh=22
    for topic in TOPICS:
        active=topic==active_topic
        tw=fTg.size(topic)[0]+16; r=pygame.Rect(bx,by,tw,bh)
        R(surf,c["acc"] if active else c["sb2"],r,11)
        if not active: pygame.draw.rect(surf,c["bdr"],r,width=1,border_radius=11)
        surf.blit(fTg.render(topic,True,(255,255,255) if active else c["sub"]),(bx+8,by+5))
        _topic_rects.append((topic,r)); bx+=tw+6

# ── Card ───────────────────────────────────────────────────────────────────────
def draw_card(surf, art, ry, is_imp, aidx, section):
    global _news_line_hits
    c = C()
    h = IMP_CARD_H if is_imp else CARD_H
    rect = pygame.Rect(CX, ry, CW, h)
    R(surf,c["imp_bg"] if is_imp else c["card"],rect,10)
    pygame.draw.rect(surf,c["imp_bdr"] if is_imp else c["bdr"],rect,width=1,border_radius=10)
    bar=c["grn"] if is_imp else (c["acc"] if mode=="global" else c["red"])
    R(surf,bar,(CX,ry+8,3,h-16),2)
    title = gtitle(art)
    sm = gsum(art)
    ver = gver(art)
    sc = gsc(art)
    al = age_lbl(art)
    img = gimg(art)
    vid = gvid(art)
    fc=factcheck.request_check(title,sm,sc)
    # Title row
    surf.blit(fB.render(clamp(title,fB,CW-60),True,c["tx"]),(CX+14,ry+8))
    if al: as_=fXs.render(al,True,c["sub"]); surf.blit(as_,(CX+CW-as_.get_width()-36,ry+9))
    # Summary — up to 4 lines for more info
    if sm:
        for li,ln in enumerate(wrap(sm,fSm,CW-28)[:4]):
            if li==3: ln=clamp(ln,fSm,CW-28)
            surf.blit(fSm.render(ln,True,c["sub"]),(CX+14,ry+28+li*16))
    # Image indicator
    img_note_y = ry + h - 42
    if img or vid:
        med_lbl = "Image & video in Details" if (img and vid) else ("Image in Details" if img else "Video in Details")
        pre = "📷 ▶ " if (img and vid) else ("📷 " if img else "▶ ")
        surf.blit(fXs.render(pre + med_lbl, True, c["acc"]), (CX + 14, img_note_y))
    # Badge row
    bx=CX+14; by2=ry+h-22
    if ver:
        lbl=f"✓ {sc} sources"; tw=fTg.size(lbl)[0]+12; br=pygame.Rect(bx,by2,tw,16)
        R(surf,c["ok"],br,8); surf.blit(fTg.render(lbl,True,c["oktx"]),(br.x+6,br.y+3)); bx+=tw+6
    if fc:
        vi=factcheck.VERDICTS.get(fc["status"],factcheck.VERDICTS["pending"])
        lbl2=vi["label"]; tw=fTg.size(lbl2)[0]+12; ar=pygame.Rect(bx,by2,tw,16)
        R(surf,vi["color"],ar,8); surf.blit(fTg.render(lbl2,True,(255,255,255)),(ar.x+6,ar.y+3))
    dr=pygame.Rect(CX+CW-30,ry+7,24,24)
    act=dot_open and dot_idx==aidx and dot_section==section
    R(surf,c["doth"] if act else c["dot"],dr,6)
    icon(surf, "dots", dr.x + 5, dr.y + 5, 14, (220, 220, 230))
    tls = wrap(title, fB, CW - 60)[:2]
    for i2, ln in enumerate(tls):
        _news_line_hits.append({"rect": pygame.Rect(CX + 14, ry + 8 + i2 * 20, CW - 52, 18), "text": ln, "font": fB})
    if sm:
        for i2, ln in enumerate(wrap(sm, fSm, CW - 28)[:3]):
            _news_line_hits.append({"rect": pygame.Rect(CX + 14, ry + 28 + i2 * 16, CW - 52, 15), "text": ln, "font": fSm})
    return rect, dr

def max_scroll():
    fi=filtered(imp_arts); fn=filtered(nrm_arts)
    if search_query: return max(0,len(search_results)*(CARD_H+GAP)+80-(WIN_H-CONTENT_TOP))
    total=28+len(fi)*(IMP_CARD_H+GAP)+20+28+len(fn)*(CARD_H+GAP)+20
    return max(0,total-(WIN_H-CONTENT_TOP))

# ── Articles view ──────────────────────────────────────────────────────────────
def draw_articles(surf):
    global _crects,_drects
    c=C(); _crects=[]; _drects=[]
    surf.set_clip(pygame.Rect(CX-8,CONTENT_TOP,WIN_W-CX+8,WIN_H-CONTENT_TOP))
    cy=CONTENT_TOP-page_scroll+8
    if loading:
        surf.set_clip(None)
        surf.blit(fB.render("Fetching & verifying news from multiple sources…",True,c["sub"]),(CX,CONTENT_TOP+20)); return
    if err and not imp_arts and not nrm_arts:
        surf.set_clip(None)
        R(surf,(55,18,18),(CX,CONTENT_TOP+8,CW,42),8)
        surf.blit(fB.render(f"  {err}",True,(255,110,110)),(CX+10,CONTENT_TOP+20)); return
    if search_query:
        surf.blit(fT.render(f'Results: "{search_query}"',True,c["acc"]),(CX,cy)); cy+=28
        if not search_results: surf.blit(fB.render("No matches found.",True,c["sub"]),(CX,cy))
        for i,art in enumerate(search_results):
            if cy+CARD_H>CONTENT_TOP and cy<WIN_H:
                cr,dr=draw_card(surf,art,cy,gimp(art),i,"srch")
                _crects.append((art,cr,"srch")); _drects.append((art,dr,i,"srch"))
            cy+=CARD_H+GAP
        surf.set_clip(None); return
    fi=filtered(imp_arts); fn=filtered(nrm_arts)
    # Important (unlimited)
    if cy>CONTENT_TOP-28 and cy<WIN_H:
        surf.blit(fT.render("⭐ Important News",True,c["grn"]),(CX,cy))
        surf.blit(fXs.render(f"last 24h · {len(fi)} stories · auto-refreshes",True,c["sub"]),
                  (CX+fT.size("⭐ Important News")[0]+8,cy+4))
    cy+=26
    if not fi and cy<WIN_H:
        surf.blit(fSm.render("No important news for this topic right now.",True,c["sub"]),(CX,cy)); cy+=22
    for i,art in enumerate(fi):
        if cy+IMP_CARD_H>CONTENT_TOP and cy<WIN_H:
            cr,dr=draw_card(surf,art,cy,True,i,"imp")
            _crects.append((art,cr,"imp")); _drects.append((art,dr,i,"imp"))
        cy+=IMP_CARD_H+GAP
    cy+=10
    if cy>CONTENT_TOP-14 and cy<WIN_H: pygame.draw.line(surf,c["bdr"],(CX,cy),(CX+CW,cy),1)
    cy+=12
    # Latest
    if cy>CONTENT_TOP-28 and cy<WIN_H:
        surf.blit(fT.render("📰 Latest News",True,c["acc"]),(CX,cy))
        surf.blit(fXs.render(f"{len(fn)} stories · new stories added on top when reloaded",True,c["sub"]),
                  (CX+fT.size("📰 Latest News")[0]+8,cy+4))
    cy+=26
    if not fn and cy<WIN_H:
        surf.blit(fSm.render("No latest news for this topic.",True,c["sub"]),(CX,cy))
    for i,art in enumerate(fn):
        if cy+CARD_H>CONTENT_TOP and cy<WIN_H:
            cr,dr=draw_card(surf,art,cy,False,i,"nrm")
            _crects.append((art,cr,"nrm")); _drects.append((art,dr,i,"nrm"))
        cy+=CARD_H+GAP
    surf.set_clip(None)

# ── Dot menu ───────────────────────────────────────────────────────────────────
def draw_dot_menu(surf):
    global _dot_st
    if not dot_open: _dot_st=None; return
    c=C()
    entry=next(((art,dr,idx,sec) for art,dr,idx,sec in _drects if idx==dot_idx and sec==dot_section),None)
    if not entry: _dot_st=None; return
    _,dr,_,_=entry
    mw=214; ih=40
    items=[("Save Article","save"),("Speak in Language","speak"),
           ("Share Article","share"),("Details","detail")]
    mh=ih*len(items)+8
    mr=pygame.Rect(dr.right-mw,dr.bottom+4,mw,mh)
    if mr.right>WIN_W-6: mr.x=WIN_W-mw-6
    if mr.bottom>WIN_H-6: mr.y=dr.y-mh-4
    sh=pygame.Surface((mw+4,mh+4),pygame.SRCALPHA); sh.fill((0,0,0,50)); surf.blit(sh,(mr.x+3,mr.y+3))
    R(surf,c["panel"],mr,12); pygame.draw.rect(surf,c["bdr"],mr,width=1,border_radius=12)
    mp=pygame.mouse.get_pos()
    dcols={"save":c["grn"],"speak":c["acc"],"share":(110,70,190),"detail":c["org"]}
    irs=[]
    for i,(lbl,key) in enumerate(items):
        r=pygame.Rect(mr.x+6,mr.y+6+i*ih,mw-12,ih-4)
        irs.append((key,r))
        if r.collidepoint(mp): R(surf,c["sb2"],r,8)
        pygame.draw.circle(surf,dcols[key],(r.x+13,r.y+r.h//2),5)
        surf.blit(fBtn.render(lbl,True,c["tx"]),(r.x+24,r.y+10))
    _dot_st=(mr,irs,dot_idx,dot_section)

# ── Detail panel ───────────────────────────────────────────────────────────────
def draw_detail(surf):
    global _detail_r, _detail_line_spans, _detail_sel_full
    if not detail_open or not detail_art:
        _detail_r = _detail_line_spans = None
        return
    c = C()
    ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    ov.fill((0, 0, 0, 175))
    surf.blit(ov, (0, 0))
    pw, ph = 760, 560
    px, py = (WIN_W - pw) // 2, (WIN_H - ph) // 2
    R(surf, c["panel"], (px, py, pw, ph), 16)
    pygame.draw.rect(surf, c["bdr"], (px, py, pw, ph), width=1, border_radius=16)
    R(surf, c["hbar"], (px, py, pw, 44), 16)
    pygame.draw.rect(surf, c["hbar"], (px, py + 24, pw, 20))
    surf.blit(fBtn.render("Article Details", True, c["sub"]), (px + 18, py + 13))
    cr = pygame.Rect(px + pw - 40, py + 9, 28, 28)
    R(surf, c["red"], cr, 6)
    surf.blit(fBtn.render("x", True, (255, 255, 255)), (cr.x + 7, cr.y + 6))
    shr_r = pygame.Rect(px + pw - 78, py + 9, 34, 28)
    R(surf, c["acc"], shr_r, 6)
    icon(surf, "share", shr_r.x + 8, shr_r.y + 5, 18, (255, 255, 255))
    art = detail_art
    acc = ""
    spans = []
    iy = py + 52
    title_lines = wrap(gtitle(art), fT, pw - 36)[:2]
    sa, sb = _detail_sel_a, _detail_sel_b
    if sa is not None and sb is not None:
        lo, hi = sorted((sa, sb))
    else:
        lo = hi = 0
    for ln in title_lines:
        if acc:
            acc += "\n"
        g0 = len(acc)
        acc += ln
        g1 = len(acc)
        rln = pygame.Rect(px + 18, iy, pw - 36, 24)
        if sa is not None and sb is not None and hi > lo:
            t0, t1 = max(lo, g0), min(hi, g1)
            if t1 > t0:
                xleft = fT.size(ln[: t0 - g0])[0] if t0 > g0 else 0
                xright = fT.size(ln[: t1 - g0])[0]
                _blit_sel_band(surf, px + 18 + xleft, iy + 2, max(1, xright - xleft), 20)
        surf.blit(fT.render(ln, True, c["tx"]), (px + 18, iy))
        spans.append((rln, g0, g1, ln, fT))
        iy += 24
    iy += 4
    al = age_lbl(art)
    if al:
        surf.blit(fXs.render(al, True, c["sub"]), (px + 18, iy))
        iy += 18
    sc, ver, imp = gsc(art), gver(art), gimp(art)
    if ver:
        bl = f"{'⭐ Important · ' if imp else ''}Verified across {sc} sources"
        bw = fTg.size(bl)[0] + 16
        br = pygame.Rect(px + 18, iy, bw, 20)
        R(surf, c["ok"], br, 10)
        surf.blit(fTg.render(bl, True, c["oktx"]), (br.x + 8, br.y + 5))
        iy += 26
    fc = factcheck.get_result(gtitle(art))
    if fc:
        vi = factcheck.VERDICTS.get(fc["status"], factcheck.VERDICTS["pending"])
        fl = vi["label"]
        bw = fTg.size(fl)[0] + 16
        far = pygame.Rect(px + 18, iy, bw, 20)
        R(surf, vi["color"], far, 10)
        surf.blit(fTg.render(fl, True, (255, 255, 255)), (far.x + 8, far.y + 5))
        iy += 26
    sm = gsum(art)
    if sm:
        surf.blit(fXs.render("Summary — drag to select, Ctrl+C copy", True, c["sub"]), (px + 18, iy))
        iy += 16
        sum_lines = wrap(sm, fSm, pw - 36)[:10]
        for ln in sum_lines:
            if acc:
                acc += "\n"
            g0 = len(acc)
            acc += ln
            g1 = len(acc)
            rln = pygame.Rect(px + 18, iy, pw - 36, 17)
            if sa is not None and sb is not None and hi > lo:
                t0, t1 = max(lo, g0), min(hi, g1)
                if t1 > t0:
                    xleft = fSm.size(ln[: t0 - g0])[0] if t0 > g0 else 0
                    xright = fSm.size(ln[: t1 - g0])[0]
                    _blit_sel_band(surf, px + 18 + xleft, iy + 1, max(1, xright - xleft), 15)
            surf.blit(fSm.render(ln, True, c["tx"]), (px + 18, iy))
            spans.append((rln, g0, g1, ln, fSm))
            iy += 17
        iy += 6
    _detail_sel_full = acc
    _detail_line_spans = spans
    img, vid = gimg(art), gvid(art)
    img_r = vid_r = None
    if img:
        surf.blit(fXs.render("📷 Image (click to open):", True, c["sub"]), (px + 18, iy))
        iy += 15
        img_r = pygame.Rect(px + 18, iy, pw - 36, 20)
        R(surf, c["sb2"], img_r, 4)
        surf.blit(fXs.render(clamp(img, fXs, pw - 44), True, c["acc"]), (px + 22, iy + 3))
        iy += 24
    if vid:
        surf.blit(fXs.render("▶ Video (click to open in browser):", True, c["sub"]), (px + 18, iy))
        iy += 15
        vid_r = pygame.Rect(px + 18, iy, pw - 36, 20)
        R(surf, c["sb2"], vid_r, 4)
        surf.blit(fXs.render(clamp(vid, fXs, pw - 44), True, c["acc"]), (px + 22, iy + 3))
        iy += 24
    lnk = glink(art)
    link_r = None
    if lnk:
        surf.blit(fXs.render("Article link (click to open):", True, c["sub"]), (px + 18, iy))
        iy += 15
        link_r = pygame.Rect(px + 18, iy, pw - 36, 20)
        R(surf, c["sb2"], link_r, 4)
        surf.blit(fXs.render(clamp(lnk, fXs, pw - 44), True, c["acc"]), (px + 22, iy + 3))
        iy += 24
    srcs = gsrcs(art)
    src_rs = []
    if srcs:
        surf.blit(fXs.render("Verified by:", True, c["sub"]), (px + 18, iy))
        iy += 16
        bx2 = px + 18
        for s in srcs[:8]:
            nm, sl = s.get("name", ""), s.get("link", "")
            lbl = f"  {nm}  "
            tw = fXs.size(lbl)[0] + 8
            if bx2 + tw > px + pw - 18:
                bx2 = px + 18
                iy += 22
            br2 = pygame.Rect(bx2, iy, tw, 18)
            R(surf, c["tag"], br2, 9)
            surf.blit(fXs.render(lbl, True, c["acc"] if sl else c["tagtx"]), (bx2 + 4, iy + 3))
            if sl:
                src_rs.append((sl, br2))
            bx2 += tw + 6
    _detail_r = (cr, link_r, img_r, vid_r, src_rs, shr_r)

# ── Settings ───────────────────────────────────────────────────────────────────
def draw_settings(surf):
    global _set_r
    c=C(); pw=500; ph=350; px=CX; py=CONTENT_TOP+6
    R(surf,c["panel"],(px,py,pw,ph),14)
    pygame.draw.rect(surf,c["bdr"],(px,py,pw,ph),width=1,border_radius=14)
    surf.blit(fT.render("Settings",True,c["tx"]),(px+18,py+14))
    rows=[("Voice Readout","voice",ai.voice.is_on),("Dark Mode","dark",dark)]
    rects=[]
    for i,(lbl,key,on) in enumerate(rows):
        ry=py+52+i*58
        R(surf,c["sb2"],(px+14,ry,pw-28,46),10)
        surf.blit(fB.render(lbl,True,c["tx"]),(px+28,ry+12))
        tr=pygame.Rect(px+pw-84,ry+9,68,28)
        pill(surf,c["ton"] if on else c["tof"],tr)
        ts=fXs.render("ON" if on else "OFF",True,(255,255,255))
        surf.blit(ts,(tr.x+(68-ts.get_width())//2,tr.y+7))
        rects.append((key,tr))
    # Language row
    ly=py+52+2*58
    R(surf,c["sb2"],(px+14,ly,pw-28,46),10)
    surf.blit(fB.render("Voice Language",True,c["tx"]),(px+28,ly+12))
    lang_rects=[]; lx=px+pw-250
    for lang in LANG_CODES:
        on=lang==app_lang
        lr=pygame.Rect(lx,ly+9,72,28)
        R(surf,c["acc"] if on else c["panel"],lr,8)
        if not on: pygame.draw.rect(surf,c["bdr"],lr,width=1,border_radius=8)
        ls=fXs.render(lang,True,(255,255,255)); surf.blit(ls,(lr.x+(72-ls.get_width())//2,lr.y+8))
        lang_rects.append((lang,lr)); lx+=78
    rects.append(("lang",lang_rects))
    
    # Logout row
    loy=py+52+3*58
    R(surf,c["sb2"],(px+14,loy,pw-28,46),10)
    surf.blit(fB.render("Account",True,c["tx"]),(px+28,loy+12))
    surf.blit(fXs.render(auth.get_email(),True,c["sub"]),(px+120,loy+14))
    lo_btn=pygame.Rect(px+pw-110,loy+9,94,28)
    R(surf,c["red"],lo_btn,8)
    ltx=fXs.render("LOGOUT",True,(255,255,255))
    surf.blit(ltx,(lo_btn.x+(94-ltx.get_width())//2,lo_btn.y+8))
    rects.append(("logout",lo_btn))

    surf.blit(fXs.render(f"Auto-reload every {AUTO_RELOAD//60}min  ·  F5=reload  ·  F8=voice  ·  {len(imp_arts)} important  ·  {len(nrm_arts)} latest  ·  {len(saved)} saved",
        True,c["sub"]),(px+18,py+ph-26))
    _set_r=rects

# ── Saved panel ────────────────────────────────────────────────────────────────
def draw_saved_panel(surf):
    global _sav_r,_sdel_r
    c=C(); _sav_r=[]; _sdel_r=[]
    px=CX; py=CONTENT_TOP; pw=CW; ph=WIN_H-py-8
    R(surf,c["panel"],(px,py,pw,ph),14)
    pygame.draw.rect(surf,c["bdr"],(px,py,pw,ph),width=1,border_radius=14)
    R(surf,c["hbar"],(px,py,pw,42),14); pygame.draw.rect(surf,c["hbar"],(px,py+24,pw,18))
    surf.blit(fT.render("Saved Articles",True,c["tx"]),(px+18,py+11))
    cs=fXs.render(f"{len(saved)} saved",True,c["sub"]); surf.blit(cs,(px+pw-cs.get_width()-16,py+16))
    if not saved:
        surf.blit(fB.render("Nothing saved yet. Use 3-dot menu on any article.",True,c["sub"]),(px+18,py+60)); return
    ih=80; vis=6; cy=py+48
    for i in range(sav_scroll,min(sav_scroll+vis,len(saved))):
        s=saved[i]; r=pygame.Rect(px+10,cy,pw-20,ih); _sav_r.append((i,r))
        R(surf,c["card"],r,8); pygame.draw.rect(surf,c["bdr"],r,width=1,border_radius=8)
        R(surf,c["grn"] if s.get("important") else c["acc"],(r.x,r.y+8,3,ih-16),2)
        surf.blit(fB.render(clamp(s["title"],fB,pw-120),True,c["tx"]),(r.x+12,r.y+8))
        if s.get("summary"):
            for li2,ln2 in enumerate(wrap(s["summary"],fSm,pw-120)[:2]):
                surf.blit(fSm.render(ln2,True,c["sub"]),(r.x+12,r.y+30+li2*16))
        bx3=r.x+12; by3=r.y+ih-20
        for tag,col2,txcol in [(s.get("source",""),c["tag"],c["tagtx"]),
                                ("✓ Verified" if s.get("verified") else "",c["ok"],c["oktx"])]:
            if tag:
                tw=fTg.size(tag)[0]+12; tr2=pygame.Rect(bx3,by3,tw,16)
                R(surf,col2,tr2,8); surf.blit(fTg.render(tag,True,txcol),(tr2.x+6,tr2.y+3)); bx3+=tw+6
        # 3-dot button same as news cards
        sav_dr=pygame.Rect(r.right-30,r.y+7,24,24)
        R(surf,c["dot"],sav_dr,6); icon(surf,"dots",sav_dr.x+5,sav_dr.y+5,14,(220,220,230))
        _sdel_r.append((i,sav_dr)); cy+=ih+5
    if len(saved)>vis:
        surf.blit(fXs.render(f"{sav_scroll+1}–{min(sav_scroll+vis,len(saved))} of {len(saved)}",
            True,c["sub"]),(px+18,cy+4))

_sav_dot_open=False; _sav_dot_idx=None; _sav_dot_st=None

def draw_saved_dot_menu(surf):
    global _sav_dot_st
    if not _sav_dot_open or _sav_dot_idx is None: _sav_dot_st=None; return
    c=C()
    dr=next((dr for i,dr in _sdel_r if i==_sav_dot_idx),None)
    if not dr: _sav_dot_st=None; return
    mw=200; ih=38; items=[("Speak in Language","speak"),("Share Article","share"),("Delete","delete")]
    mh=ih*len(items)+8
    mr=pygame.Rect(dr.right-mw,dr.bottom+4,mw,mh)
    if mr.right>WIN_W-6: mr.x=WIN_W-mw-6
    if mr.bottom>WIN_H-6: mr.y=dr.y-mh-4
    sh=pygame.Surface((mw+4,mh+4),pygame.SRCALPHA); sh.fill((0,0,0,50)); surf.blit(sh,(mr.x+3,mr.y+3))
    R(surf,c["panel"],mr,12); pygame.draw.rect(surf,c["bdr"],mr,width=1,border_radius=12)
    mp=pygame.mouse.get_pos()
    dcols={"speak":c["acc"],"share":(110,70,190),"delete":c["red"]}
    irs=[]
    for i,(lbl,key) in enumerate(items):
        r2=pygame.Rect(mr.x+6,mr.y+6+i*ih,mw-12,ih-4)
        irs.append((key,r2))
        if r2.collidepoint(mp): R(surf,c["sb2"],r2,8)
        pygame.draw.circle(surf,dcols[key],(r2.x+13,r2.y+r2.h//2),5)
        surf.blit(fBtn.render(lbl,True,c["tx"]),(r2.x+24,r2.y+9))
    _sav_dot_st=(mr,irs,_sav_dot_idx)

# ── Weather panel ──────────────────────────────────────────────────────────────
def wx_hydrated_city_rows():
    if not wx_country:
        return []
    rows = []
    for city, la, lo in wx.cities_for(wx_country):
        rows.append((city, la, lo, city))
    return rows


def draw_weather(surf):
    global _wx_c_rects, _wx_city_rects, _wx_country_col_rect, _wx_city_col_rect
    global _wx_country_col_hit, _wx_city_col_hit, _wx_vis_c, _wx_vis_city, _wx_city_row_count
    global wx_c_search_rect, wx_city_search_rect, wx_c_query, wx_city_query, wx_active_input
    c = C()
    _wx_c_rects = []
    _wx_city_rects = []
    _wx_country_col_rect = _wx_city_col_rect = _wx_country_col_hit = _wx_city_col_hit = None
    px, py, pw = CX, CONTENT_TOP, CW
    ph = WIN_H - py - 8
    R(surf, c["panel"], (px, py, pw, ph), 14)
    pygame.draw.rect(surf, c["bdr"], (px, py, pw, ph), width=1, border_radius=14)
    R(surf, c["hbar"], (px, py, pw, 42), 14)
    pygame.draw.rect(surf, c["hbar"], (px, py + 24, pw, 18))
    surf.blit(fT.render("Weather", True, c["tx"]), (px + 18, py + 11))
    countries = [c_name for c_name in wx.COUNTRY_NAMES if wx_c_query.lower() in c_name.lower()]
    nco = len(countries)
    cw = pw // 3
    row_h = 30
    list_top = py + 84
    list_bot = py + ph - 10
    avail_h = max(row_h, list_bot - list_top)
    vis_c = max(1, min(20, avail_h // row_h))
    _wx_vis_c = vis_c
    
    wx_c_search_rect = pygame.Rect(px + 8, py + 48, cw - 16, 28)
    R(surf, c["srch_bg"], wx_c_search_rect, 6)
    pygame.draw.rect(surf, c["srch_bdr"] if wx_active_input=="country" else c["bdr"], wx_c_search_rect, width=1, border_radius=6)
    surf.blit(fBtn.render(wx_c_query if wx_c_query else f"Search Countries ({nco})...", True, c["tx"] if wx_c_query else c["sub"]), (px + 14, py + 54))

    wx_city_search_rect = pygame.Rect(px + cw + 8, py + 48, cw - 16, 28)
    R(surf, c["srch_bg"], wx_city_search_rect, 6)
    pygame.draw.rect(surf, c["srch_bdr"] if wx_active_input=="city" else c["bdr"], wx_city_search_rect, width=1, border_radius=6)
    surf.blit(fBtn.render(wx_city_query if wx_city_query else "Search Cities...", True, c["tx"] if wx_city_query else c["sub"]), (px + cw + 14, py + 54))

    surf.blit(fBtn.render("Current Weather", True, c["sub"]), (px + cw * 2 + 14, py + 48))
    cy_ = list_top
    for ci in range(wx_c_scroll, min(wx_c_scroll + vis_c, nco)):
        ctry = countries[ci]
        active = ctry == wx_country
        r = pygame.Rect(px + 8, cy_, cw - 16, 26)
        R(surf, c["acc"] if active else c["sb2"], r, 6)
        surf.blit(fBtn.render(clamp(ctry, fBtn, cw - 24), True, (255, 255, 255) if active else c["tx"]), (r.x + 8, r.y + 6))
        _wx_c_rects.append((ctry, r))
        cy_ += row_h
    if wx_c_scroll > 0:
        surf.blit(fXs.render("▲ scroll", True, c["sub"]), (px + 8, py + 64))
    if wx_c_scroll + vis_c < nco:
        surf.blit(fXs.render("▼ more", True, c["sub"]), (px + 8, cy_))
    _wx_country_col_rect = pygame.Rect(px + 8, list_top, cw - 16, vis_c * row_h)
    _wx_country_col_hit = pygame.Rect(px + 8, list_top, cw - 16, list_bot - list_top)

    city_list_top = list_top
    vis_city = max(1, min(20, (list_bot - city_list_top) // row_h))
    all_city_rows = wx_hydrated_city_rows() if wx_country else []
    city_rows = [cr for cr in all_city_rows if wx_city_query.lower() in cr[0].lower()]
    _wx_city_row_count = len(city_rows)
    _wx_vis_city = vis_city if wx_country else 0
    cy2 = city_list_top
    if wx_country:
        _wx_city_col_hit = pygame.Rect(px + cw + 8, list_top, cw - 16, list_bot - list_top)
        if not city_rows:
            surf.blit(fSm.render("Loading cities… (needs internet once)", True, c["sub"]), (px + cw + 10, cy2 + 2))
            cy2 += 22
        for j in range(wx_city_scroll, min(wx_city_scroll + vis_city, len(city_rows))):
            label, lat, lon, cnm = city_rows[j]
            active = cnm == wx_city
            r2 = pygame.Rect(px + cw + 8, cy2, cw - 16, 26)
            R(surf, c["acc"] if active else c["sb2"], r2, 6)
            surf.blit(fBtn.render(clamp(label, fBtn, cw - 24), True, (255, 255, 255) if active else c["tx"]), (r2.x + 8, r2.y + 6))
            _wx_city_rects.append((cnm, lat, lon, r2))
            cy2 += row_h
        if wx_city_scroll > 0:
            surf.blit(fXs.render("▲", True, c["sub"]), (px + cw + 8, city_list_top - 4))
        if wx_country and wx_city_scroll + vis_city < len(city_rows):
            surf.blit(fXs.render("▼", True, c["sub"]), (px + cw + 8, cy2))
        col_h = min(len(city_rows), vis_city) * row_h if city_rows else 22
        _wx_city_col_rect = pygame.Rect(px + cw + 8, city_list_top, cw - 16, max(col_h, 1))
    else:
        _wx_city_col_hit = None
        surf.blit(fSm.render("← Select a country", True, c["sub"]), (px + cw + 10, city_list_top + 4))

    wx3 = px + cw * 2 + 14
    wy = list_top
    if wx_loading:
        surf.blit(fB.render("Loading…", True, c["sub"]), (wx3, wy))
    elif wx_data:
        d = wx_data
        if "error" in d:
            surf.blit(fXs.render(f"Error: {d['error'][:40]}", True, c["red"]), (wx3, wy))
        else:
            ico = wx.wicon(d["code"])
            surf.blit(fH.render(f"{ico} {d['temp']}°C", True, c["tx"]), (wx3, wy))
            wy += 38
            surf.blit(fB.render(d["desc"], True, c["sub"]), (wx3, wy))
            wy += 24
            surf.blit(fSm.render(f"Feels like {d['feels']}°C", True, c["sub"]), (wx3, wy))
            wy += 18
            surf.blit(fSm.render(f"Humidity {d['humidity']}%   Wind {d['wind']} km/h", True, c["sub"]), (wx3, wy))
            wy += 18
            if d.get("precip", 0) > 0:
                surf.blit(fSm.render(f"Rain {d['precip']} mm", True, c["acc"]), (wx3, wy))
                wy += 18
            surf.blit(fXs.render(d["city"], True, c["acc"]), (wx3, wy))
            wy += 20
            surf.blit(fXs.render("5-Day Forecast", True, c["sub"]), (wx3, wy))
            wy += 16
            for fc2 in d.get("forecast", []):
                date = fc2["date"][5:]
                desc = fc2["desc"][:14]
                mx2 = fc2.get("max")
                mn = fc2.get("min")
                rain = fc2.get("rain", 0)
                ts = f"{mx2:.0f}/{mn:.0f}°C" if mx2 is not None else ""
                rs = f" 🌧{rain:.0f}mm" if rain and rain > 0.5 else ""
                surf.blit(fXs.render(f"{date}  {desc:<16} {ts}{rs}", True, c["tx"]), (wx3, wy))
                wy += 17

# ── Frame ──────────────────────────────────────────────────────────────────────
def draw_frame(surf):
    global _news_line_hits
    _news_line_hits = []
    c = C()
    surf.fill(c["bg"])
    draw_sidebar(surf)
    draw_topbar(surf)
    draw_topic_bar(surf)
    if panel=="saved":
        draw_saved_panel(surf)
        draw_saved_dot_menu(surf)
    elif panel=="weather":
        draw_weather(surf)
    elif panel=="settings":
        draw_articles(surf)
        draw_settings(surf)
    else:
        draw_articles(surf)
        draw_dot_menu(surf)
    draw_detail(surf)
    draw_notifs(surf)
    pygame.display.flip()

# ── Events ─────────────────────────────────────────────────────────────────────
def sb_click(mx,my):
    global panel,dot_open,page_scroll
    if not(0<mx<SIDEBAR_W): return False
    y=58
    for key,_,_ in SB:
        if pygame.Rect(5,y,SIDEBAR_W-10,40).collidepoint(mx,my):
            dot_open=False
            if key in("global","india"): load_news(key); panel=None; page_scroll=0
            elif key=="settings": panel=None if panel=="settings" else "settings"
            elif key=="saved":    panel=None if panel=="saved"    else "saved"
            elif key=="weather":  panel=None if panel=="weather"  else "weather"
            return True
        y+=46
    return False

def set_click(mx,my):
    global dark,app_lang,set_active_input
    set_active_input = None
    if not _set_r: return False
    for item in _set_r:
        key,val=item[0],item[1]
        if key=="lang":
            for lang,r in val:
                if r.collidepoint(mx,my):
                    app_lang=lang; ai.voice_lang=LANG_CODES[lang]; return True
        elif val.collidepoint(mx,my):
            if key=="voice": ai.toggle_voice()
            elif key=="dark": dark=not dark
            elif key=="logout":
                auth.logout()
                run_auth_loop()
                # Re-check country and news after switching user
                global home_country, saved
                home_country = auth.get_user_country()
                # Note: real country picker logic is outside main loop, 
                # so for now a simple restart of the app script is best
                # but we can just set panel=None and let it continue.
                # To be safe, we refresh saved news:
                saved = auth.cloud_load_news()
                write_saved()
                load_news(mode, force=True)
            return True
    return False

def dot_menu_click(mx,my):
    global dot_open,detail_open,detail_art,_detail_sel_a,_detail_sel_b,_detail_text_drag
    if not _dot_st: return False
    mr,irs,idx,sec=_dot_st
    if not mr.collidepoint(mx,my): dot_open=False; return False
    for key,r in irs:
        if r.collidepoint(mx,my):
            match=next((art for art,_,i,s in _drects if i==idx and s==sec),None)
            if match:
                if key=="save": do_save(match)
                elif key=="speak": ai.speak_article(gtitle(match),gsum(match),LANG_CODES.get(app_lang,"hi"))
                elif key=="share": share_article(match)
                elif key=="detail":
                    detail_art=match; detail_open=True
                    _detail_sel_a=_detail_sel_b=None; _detail_text_drag=False
            dot_open=False; return True
    return False

def dot_click(mx,my):
    global dot_open,dot_idx,dot_section
    for art,dr,idx,sec in _drects:
        if dr.collidepoint(mx,my):
            if dot_open and dot_idx==idx and dot_section==sec: dot_open=False
            else: dot_open=True; dot_idx=idx; dot_section=sec
            return True
    return False

def detail_click(mx,my):
    global detail_open, _detail_text_drag, _detail_sel_a, _detail_sel_b
    if not _detail_r:
        return
    cr, link_r, img_r, vid_r, src_rs, shr_r = _detail_r
    if cr and cr.collidepoint(mx, my):
        detail_open = False
        _detail_text_drag = False
        _detail_sel_a = _detail_sel_b = None
        return
    if shr_r and shr_r.collidepoint(mx, my):
        share_article(detail_art)
        return
    if link_r and link_r.collidepoint(mx, my):
        try:
            webbrowser.open(glink(detail_art))
        except Exception:
            pass
        return
    if img_r and img_r.collidepoint(mx, my):
        try:
            webbrowser.open(gimg(detail_art))
        except Exception:
            pass
        return
    if vid_r and vid_r.collidepoint(mx, my):
        vu = gvid(detail_art)
        if vu:
            try:
                webbrowser.open(vu)
            except Exception:
                pass
        return
    for url, br in (src_rs or []):
        if br.collidepoint(mx, my):
            try:
                webbrowser.open(url)
            except Exception:
                pass
            return
    gi = _detail_sel_index_at(mx, my)
    if gi is not None:
        _detail_sel_a = _detail_sel_b = gi
        _detail_text_drag = True


def _try_start_news_line_drag(mx, my):
    global _news_line_drag, _news_line_hit, _news_sel_ch0, _news_sel_ch1
    if dot_open or search_active or panel is not None:
        return False
    for hit in _news_line_hits:
        if hit["rect"].collidepoint(mx, my):
            _news_line_hit = hit
            dx = mx - hit["rect"].x
            _news_sel_ch0 = _news_sel_ch1 = _char_at_x_in_line(hit["font"], hit["text"], dx)
            _news_line_drag = True
            return True
    return False

def saved_dot_click(mx,my):
    global _sav_dot_open,_sav_dot_idx
    for i,dr in _sdel_r:
        if dr.collidepoint(mx,my):
            if _sav_dot_open and _sav_dot_idx==i: _sav_dot_open=False
            else: _sav_dot_open=True; _sav_dot_idx=i
            return True
    return False

def saved_dot_menu_click(mx,my):
    global _sav_dot_open
    if not _sav_dot_st: return False
    mr,irs,idx=_sav_dot_st
    if not mr.collidepoint(mx,my): _sav_dot_open=False; return False
    for key,r in irs:
        if r.collidepoint(mx,my):
            if 0<=idx<len(saved):
                s=saved[idx]
                if key=="speak": ai.speak_article(s["title"],s.get("summary",""),LANG_CODES.get(app_lang,"hi"))
                elif key=="share": share_article(s)
                elif key=="delete": rm_saved(idx)
            _sav_dot_open=False; return True
    return False

def wx_click(mx,my):
    global wx_country, wx_city, wx_data, wx_loading, wx_city_scroll, search_active
    global wx_active_input, wx_c_query, wx_city_query
    search_active = False
    wx_active_input = None
    if wx_c_search_rect and wx_c_search_rect.collidepoint(mx,my):
        wx_active_input = "country"
        return True
    if wx_city_search_rect and wx_city_search_rect.collidepoint(mx,my):
        wx_active_input = "city"
        return True
    for ctry, r in _wx_c_rects:
        if r.collidepoint(mx,my):
            wx_country = ctry
            wx_city = None
            wx_data = None
            wx_city_scroll = 0
            return True
    for cnm, lat, lon, r in _wx_city_rects:
        if r.collidepoint(mx,my):
            wx_city = cnm
            wx_data = None
            wx_loading = True

            def _cb(d):
                global wx_data, wx_loading
                wx_data = d
                wx_loading = False

            wx.fetch_weather(cnm, lat, lon, _cb)
            return True
    return False


def handle_search_key(event):
    global search_query,search_results,search_sel_s,search_sel_e
    ctrl=pygame.key.get_mods()&pygame.KMOD_CTRL
    if ctrl and event.key==pygame.K_v:
        try:
            p=paste_from_clipboard()
            if p:
                if search_sel_s is not None and search_sel_e is not None and search_sel_s!=search_sel_e:
                    a,b=sorted([search_sel_s,search_sel_e])
                    search_query=search_query[:a]+p+search_query[b:]
                    search_sel_s=search_sel_e=a+len(p)
                else:
                    pos=search_sel_e or len(search_query)
                    search_query=search_query[:pos]+p+search_query[pos:]
                    search_sel_s=search_sel_e=pos+len(p)
        except: pass
    elif ctrl and event.key==pygame.K_a:
        search_sel_s=0; search_sel_e=len(search_query)
    elif ctrl and event.key==pygame.K_c:
        sel=get_sel()
        if sel:
            try: copy_to_clipboard(sel)
            except: pass
    elif event.key==pygame.K_BACKSPACE:
        if search_sel_s is not None and search_sel_e is not None and search_sel_s!=search_sel_e:
            a,b=sorted([search_sel_s,search_sel_e])
            search_query=search_query[:a]+search_query[b:]
            search_sel_s=search_sel_e=a
        elif search_query:
            pos=search_sel_e if search_sel_e is not None else len(search_query)
            if pos>0: search_query=search_query[:pos-1]+search_query[pos:]; search_sel_s=search_sel_e=pos-1
    elif event.key==pygame.K_DELETE:
        pos=search_sel_e if search_sel_e is not None else len(search_query)
        if pos<len(search_query): search_query=search_query[:pos]+search_query[pos+1:]
    elif event.key in(pygame.K_LEFT,pygame.K_RIGHT,pygame.K_HOME,pygame.K_END):
        pos=search_sel_e if search_sel_e is not None else len(search_query)
        if event.key==pygame.K_LEFT: pos=max(0,pos-1)
        elif event.key==pygame.K_RIGHT: pos=min(len(search_query),pos+1)
        elif event.key==pygame.K_HOME: pos=0
        elif event.key==pygame.K_END: pos=len(search_query)
        search_sel_s=search_sel_e=pos
    elif event.unicode and event.unicode.isprintable():
        if search_sel_s is not None and search_sel_e is not None and search_sel_s!=search_sel_e:
            a,b=sorted([search_sel_s,search_sel_e])
            search_query=search_query[:a]+event.unicode+search_query[b:]
            search_sel_s=search_sel_e=a+1
        else:
            pos=search_sel_e if search_sel_e is not None else len(search_query)
            search_query=search_query[:pos]+event.unicode+search_query[pos:]
            search_sel_s=search_sel_e=pos+1
    do_search(search_query)

# ── Main loop ──────────────────────────────────────────────────────────────────
load_settings()
load_saved()

# ── Auth screen loop ──────────────────────────────────────────────────────────
def run_auth_loop():
    global _auth_mode, _auth_email, _auth_pass, _auth_msg, _auth_msg_clr, _auth_focus, _auth_loading
    while True:
        email_r, pass_r, btn_r, tog_r = draw_auth_screen(screen)
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); exit()
            elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                mx,my=event.pos
                if email_r.collidepoint(mx,my): _auth_focus="email"
                elif pass_r.collidepoint(mx,my): _auth_focus="pass"
                elif btn_r.collidepoint(mx,my):
                    if not _auth_email or not _auth_pass:
                        _auth_msg="Please fill in both fields."; _auth_msg_clr=C()["red"]
                    else:
                        _auth_loading=True
                        draw_auth_screen(screen)
                        if _auth_mode=="register":
                            ok,msg=auth.register(_auth_email,_auth_pass)
                            _auth_msg=msg
                            _auth_msg_clr=C()["grn"] if ok else C()["red"]
                            if ok: _auth_mode="login"; _auth_pass=""
                        else:
                            ok,msg=auth.login(_auth_email,_auth_pass)
                            _auth_msg=msg
                            _auth_msg_clr=C()["grn"] if ok else C()["red"]
                            if ok:
                                _auth_loading=False
                                return  # success!
                        _auth_loading=False
                elif tog_r.collidepoint(mx,my):
                    _auth_mode="register" if _auth_mode=="login" else "login"
                    _auth_msg=""
            elif event.type==pygame.KEYDOWN:
                ctrl=pygame.key.get_mods()&pygame.KMOD_CTRL
                if ctrl and event.key==pygame.K_v:
                    try:
                        p=pyperclip.paste()
                        if p:
                            p=p.strip()
                            if _auth_focus=="email": _auth_email+=p
                            else: _auth_pass+=p
                    except: pass
                elif ctrl and event.key==pygame.K_c:
                    try:
                        if _auth_focus=="email": copy_to_clipboard(_auth_email)
                        else: copy_to_clipboard(_auth_pass)
                    except: pass
                elif ctrl and event.key==pygame.K_a:
                    pass  # select all (no visual selection in this simple UI)
                elif event.key==pygame.K_TAB:
                    _auth_focus="pass" if _auth_focus=="email" else "email"
                elif event.key==pygame.K_RETURN:
                    pygame.event.post(pygame.event.Event(pygame.MOUSEBUTTONDOWN,button=1,pos=(btn_r.centerx,btn_r.centery)))
                elif event.key==pygame.K_BACKSPACE:
                    if _auth_focus=="email": _auth_email=_auth_email[:-1]
                    else: _auth_pass=_auth_pass[:-1]
                elif event.unicode and event.unicode.isprintable():
                    if _auth_focus=="email": _auth_email+=event.unicode
                    else: _auth_pass+=event.unicode
        pygame.time.Clock().tick(30)

# Initialize Firebase
auth.init()

# Try auto-login from saved session
if not auth.try_auto_login():
    run_auth_loop()

# ── Country picker loop (on first login) ──────────────────────────────────────
home_country = auth.get_user_country()
if not home_country:
    _cp_sel=None; _cp_scroll=0; _cp_query=""
    running_cp=True
    while running_cp:
        rects_cp, btn_cp, sr_cp, countries_cp = draw_country_picker(screen, _cp_sel, _cp_scroll, _cp_query)
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); exit()
            elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
                mx,my=event.pos
                for cn,cr in rects_cp:
                    if cr.collidepoint(mx,my): _cp_sel=cn
                if btn_cp.collidepoint(mx,my) and _cp_sel:
                    home_country=_cp_sel
                    auth.save_user_country(home_country)
                    running_cp=False
            elif event.type==pygame.KEYDOWN:
                if event.key==pygame.K_BACKSPACE: _cp_query=_cp_query[:-1]; _cp_scroll=0
                elif event.key==pygame.K_ESCAPE: _cp_query=""; _cp_scroll=0
                elif event.unicode and event.unicode.isprintable(): _cp_query+=event.unicode; _cp_scroll=0
            elif event.type==pygame.MOUSEWHEEL:
                mx2,my2=pygame.mouse.get_pos()
                maxs=max(0,len(countries_cp)-10)
                _cp_scroll=max(0,min(maxs,_cp_scroll-event.y))
        pygame.time.Clock().tick(30)

# ── Language picker loop ──────────────────────────────────────────────────────
running_lang=True
while running_lang:
    lang_rects_l,confirm_r=draw_lang_picker(screen)
    for event in pygame.event.get():
        if event.type==pygame.QUIT: pygame.quit(); exit()
        elif event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            mx,my=event.pos
            for lang,r in lang_rects_l:
                if r.collidepoint(mx,my):
                    app_lang=lang; ai.voice_lang=LANG_CODES[lang]
            if confirm_r.collidepoint(mx,my):
                running_lang=False

# Load cloud-synced saved news
if auth.is_logged_in():
    cloud_saved = auth.cloud_load_news()
    if cloud_saved:
        saved = cloud_saved
        write_saved()  # Also save locally as backup

load_news("global")
clock=pygame.time.Clock(); running=True; mouse_on_search=False

while running:
    auto_reload_tick()
    draw_frame(screen)
    for event in pygame.event.get():
        if event.type==pygame.QUIT: running=False
        elif event.type == pygame.VIDEORESIZE:
            if not is_fullscreen:
                win_size = (event.w, event.h)
                update_dimensions(event.w, event.h)
                screen = pygame.display.set_mode(win_size, pygame.RESIZABLE)
        elif event.type==pygame.KEYDOWN:
            k=event.key; ctrl=pygame.key.get_mods()&pygame.KMOD_CTRL
            if k == pygame.K_F5 and panel != "weather":
                load_news(mode, force=True)
            elif k == pygame.K_F8:
                ai.toggle_voice()
                push_notif("Voice " + ("ON" if ai.voice.is_on else "OFF"))
            elif detail_open and ctrl and k == pygame.K_c and _detail_sel_full:
                a, b = sorted((_detail_sel_a if _detail_sel_a is not None else 0, _detail_sel_b if _detail_sel_b is not None else 0))
                if a != b:
                    try:
                        copy_to_clipboard(_detail_sel_full[a:b])
                        push_notif("Copied selection")
                    except Exception:
                        pass
            elif detail_open and ctrl and k == pygame.K_a and _detail_sel_full:
                _detail_sel_a = 0
                _detail_sel_b = len(_detail_sel_full)
            elif search_active and not detail_open:
                handle_search_key(event)
                if k==pygame.K_ESCAPE: search_active=False; search_query=""; search_results=[]
            elif wx_active_input and panel=="weather":
                if k==pygame.K_ESCAPE: 
                    wx_active_input=None
                elif k==pygame.K_BACKSPACE:
                    if wx_active_input=="country": wx_c_query=wx_c_query[:-1]
                    else: wx_city_query=wx_city_query[:-1]
                elif event.unicode and event.unicode.isprintable():
                    if wx_active_input=="country": wx_c_query+=event.unicode
                    else: wx_city_query+=event.unicode
                if wx_active_input=="country": wx_c_scroll=0
                else: wx_city_scroll=0
            elif k==pygame.K_ESCAPE:
                if detail_open:
                    detail_open=False
                    _detail_text_drag=False
                    _detail_sel_a=_detail_sel_b=None
                elif dot_open: dot_open=False
                elif _sav_dot_open: _sav_dot_open=False  # type: ignore
                elif panel: panel=None
                else: running=False
            elif ctrl and k==pygame.K_r and panel!="weather":
                load_news(mode,force=True)
            elif not detail_open:
                if panel=="saved":
                    if k==pygame.K_UP: sav_scroll=max(0,sav_scroll-1)
                    elif k==pygame.K_DOWN: sav_scroll=min(max(0,len(saved)-6),sav_scroll+1)
                elif panel=="weather":
                    mxk, myk = pygame.mouse.get_pos()
                    nco = len(wx.COUNTRY_NAMES)
                    nrow = _wx_city_row_count
                    vmax_c = max(0, nco - _wx_vis_c)
                    vmax_city = max(0, nrow - _wx_vis_city)
                    over_city = bool(wx_country and _wx_city_col_hit and _wx_city_col_hit.collidepoint(mxk, myk))
                    over_country = bool(_wx_country_col_hit and _wx_country_col_hit.collidepoint(mxk, myk))
                    if over_city and nrow > 0:
                        if k == pygame.K_UP:
                            wx_city_scroll = max(0, wx_city_scroll - 1)
                        elif k == pygame.K_DOWN and vmax_city > 0:
                            wx_city_scroll = min(vmax_city, wx_city_scroll + 1)
                    elif over_country:
                        if k == pygame.K_UP:
                            wx_c_scroll = max(0, wx_c_scroll - 1)
                        elif k == pygame.K_DOWN:
                            wx_c_scroll = min(vmax_c, wx_c_scroll + 1)
                else:
                    if k==pygame.K_UP: page_scroll=max(0,page_scroll-40)
                    elif k==pygame.K_DOWN: page_scroll=min(max_scroll(),page_scroll+40)
        elif event.type==pygame.MOUSEBUTTONDOWN:
            mx,my=event.pos
            if event.button==1:
                if search_rect and search_rect.collidepoint(mx,my):
                    search_active=True; pos=char_at_x(mx)
                    search_sel_s=search_sel_e=pos; mouse_on_search=True
                    show_keyboard()
                elif detail_open:
                    detail_click(mx,my)
                elif _try_start_news_line_drag(mx,my):
                    pass
                elif _sav_dot_open:
                    if not saved_dot_menu_click(mx,my): _sav_dot_open=False  # type: ignore
                elif dot_open:
                    if not dot_menu_click(mx,my): dot_open=False
                elif search_clear_r and search_clear_r.collidepoint(mx,my):
                    search_query=""; search_results=[]; search_sel_s=search_sel_e=None
                elif reload_rect and reload_rect.collidepoint(mx,my): load_news(mode,force=True)
                elif panel in("saved","weather",None,"settings"):
                    tp_hit=False
                    if panel not in("saved","weather"):
                        for topic,r in _topic_rects:
                            if r.collidepoint(mx,my):
                                active_topic=topic; page_scroll=0; tp_hit=True; break
                    if not tp_hit:
                        if not sb_click(mx,my):
                            if panel=="settings": set_click(mx,my)
                            elif panel=="saved":
                                if not saved_dot_menu_click(mx,my):
                                    saved_dot_click(mx,my)
                            elif panel=="weather": wx_click(mx,my)
                            else:
                                search_active=False
                                hide_keyboard()
                                if not dot_click(mx,my): pass  # cards don't open popup
            elif not detail_open:
                spd=60
                if panel=="saved":
                    if event.button==4: sav_scroll=max(0,sav_scroll-1)
                    elif event.button==5: sav_scroll=min(max(0,len(saved)-6),sav_scroll+1)
                elif panel=="weather":
                    mxw, myw = event.pos
                    nco = len(wx.COUNTRY_NAMES)
                    nrow = _wx_city_row_count
                    vmax_c = max(0, nco - _wx_vis_c)
                    vmax_city = max(0, nrow - _wx_vis_city)
                    over_city = bool(wx_country and _wx_city_col_hit and _wx_city_col_hit.collidepoint(mxw, myw))
                    over_country = bool(_wx_country_col_hit and _wx_country_col_hit.collidepoint(mxw, myw))
                    if over_city and nrow > 0 and vmax_city > 0:
                        if event.button == 4:
                            wx_city_scroll = max(0, wx_city_scroll - 1)
                        elif event.button == 5:
                            wx_city_scroll = min(vmax_city, wx_city_scroll + 1)
                    elif over_country:
                        if event.button == 4:
                            wx_c_scroll = max(0, wx_c_scroll - 1)
                        elif event.button == 5:
                            wx_c_scroll = min(vmax_c, wx_c_scroll + 1)
                else:
                    if event.button==4: page_scroll=max(0,page_scroll-spd)
                    elif event.button==5: page_scroll=min(max_scroll(),page_scroll+spd)
        elif event.type==pygame.MOUSEBUTTONUP:
            if event.button==1:
                mouse_on_search=False
                if _news_line_drag and _news_line_hit:
                    a,b=sorted((_news_sel_ch0,_news_sel_ch1))
                    if a!=b:
                        sn=_news_line_hit["text"][a:b]
                        if sn.strip():
                            try:
                                copy_to_clipboard(sn)
                                push_notif("Copied text")
                            except Exception:
                                pass
                _news_line_drag=False
                _detail_text_drag=False
        elif event.type==pygame.MOUSEMOTION:
            if mouse_on_search and search_rect and search_rect.collidepoint(*event.pos):
                search_sel_e=char_at_x(event.pos[0])
            elif _detail_text_drag and detail_open:
                g=_detail_sel_index_at(*event.pos)
                if g is not None:
                    _detail_sel_b=g
            elif _news_line_drag and _news_line_hit:
                if _news_line_hit["rect"].collidepoint(*event.pos):
                    _news_sel_ch1=_char_at_x_in_line(_news_line_hit["font"],_news_line_hit["text"],event.pos[0]-_news_line_hit["rect"].x)
    clock.tick(30)
pygame.quit()