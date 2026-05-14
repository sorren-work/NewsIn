"""
Rule-based fact checker — no API key needed.
Fast, offline, runs in background threads.
"""
import re, threading, hashlib, time

_cache = {}
_lock  = threading.Lock()
_queue = []
_running = False

API_KEY = None

VERDICTS = {
    "verified":   {"label": "AI Approved ✔", "color": (22,130,55),  "icon": "✔"},
    "suspicious": {"label": "AI FLAGGED ⚠",  "color": (190,100,0),  "icon": "⚠"},
    "pending":    {"label": "Checking…",      "color": (60,100,180), "icon": "·"},
}

_CLICKBAIT = re.compile(
    r"\b(you won'?t believe|shocking!|mind.?blow|they don'?t want you|"
    r"what happen(?:ed|s) next|the truth about|exposed!|breaking!!|"
    r"must.?see|miracle cure|100% guaranteed|instantly|never before seen|"
    r"doctors hate|this one trick|secret they|wake up|sheeple)\b", re.I)

_CREDIBLE = re.compile(
    r"\b(minister|president|prime minister|government|parliament|senate|"
    r"court|police|official|report|confirmed|announced|signed|launched|"
    r"approved|killed|injured|arrested|elected|summit|treaty|ceasefire|"
    r"earthquake|flood|attack|protest|investigation|statement|declared)\b", re.I)

def _h(title): return hashlib.md5(title.lower().strip().encode()).hexdigest()[:14]

def _check(title, summary, sc):
    if API_KEY:
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                import google.generativeai as genai
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel('gemini-2.5-flash')
            prompt = f"You are a fact checker. Review this news article. Respond with exactly one word: VERIFIED if it is likely true and from a credible source, or SUSPICIOUS if it uses clickbait, fake news patterns, or lacks credibility. Title: {title}. Summary: {summary}."
            resp = model.generate_content(prompt)
            text = resp.text.strip().lower()
            if "verified" in text: return "verified"
            if "suspicious" in text: return "suspicious"
        except Exception as e:
            print(f"Gemini AI error: {e}")
            pass # Fallback to heuristic
    
    score = 0
    # Clickbait patterns
    cb = _CLICKBAIT.findall(title+" "+(summary or ""))
    score += len(cb)*2
    # Excessive caps
    if len(re.findall(r'\b[A-Z]{4,}\b', title)) > 1: score += 2
    # Multiple exclamation/question marks
    if title.count('!')>1 or title.count('?')>1: score += 2
    # No credible event keywords
    if not _CREDIBLE.search(title+" "+(summary or "")): score += 1
    # More sources = more credible
    score -= min(sc, 4)
    return "suspicious" if score >= 3 else "verified"

def _worker():
    global _running
    while True:
        with _lock:
            if not _queue: _running=False; return
            h,title,summary,sc = _queue.pop(0)
        with _lock:
            if h in _cache and _cache[h]["status"]!="pending": continue
        status = _check(title, summary, sc)
        with _lock:
            _cache[h] = {"status":status,"ts":time.time()}

def request_check(title, summary="", source_count=1):
    global _running
    h = _h(title)
    with _lock:
        if h in _cache: return _cache[h]
        _cache[h] = {"status":"pending","ts":time.time()}
        _queue.append((h,title,summary,source_count))
        if not _running:
            _running=True
            threading.Thread(target=_worker,daemon=True).start()
    return _cache[h]

def get_result(title):
    h = _h(title)
    with _lock: return _cache.get(h)