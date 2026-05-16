import json, os, threading, requests, time

FIREBASE_CONFIG_FILE = "firebase_config.json"
SESSION_FILE = "session.json"

_config = None
_user = None  # Current logged-in user info
_user_info = None

def _load_config():
    global _config
    if os.path.exists(FIREBASE_CONFIG_FILE):
        try:
            with open(FIREBASE_CONFIG_FILE, "r") as f:
                _config = json.load(f)
                return _config
        except: pass
    return None

def _save_session():
    if _user:
        try:
            with open(SESSION_FILE, "w") as f:
                json.dump({
                    "email": _user.get("email", ""),
                    "refreshToken": _user.get("refreshToken", ""),
                    "idToken": _user.get("idToken", ""),
                    "localId": _user.get("localId", ""),
                }, f)
        except: pass

def _load_session():
    global _user, _user_info
    if not _config or not os.path.exists(SESSION_FILE):
        return False
    try:
        with open(SESSION_FILE, "r") as f:
            session = json.load(f)
        
        # Refresh token
        url = f"https://securetoken.googleapis.com/v1/token?key={_config['apiKey']}"
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": session.get("refreshToken", "")
        }
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            _user = {
                "idToken": data["id_token"],
                "refreshToken": data["refresh_token"],
                "localId": data["user_id"],
                "email": session.get("email", ""),
            }
            _save_session()
            return True
    except Exception as e:
        print(f"Session restore failed: {e}")
        if os.path.exists(SESSION_FILE):
            try: os.remove(SESSION_FILE)
            except: pass
    return False

def init():
    return _load_config() is not None

def try_auto_login():
    return _load_session()

def register(email, password):
    if not _config: return False, "Not initialized"
    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={_config['apiKey']}"
        resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
        if resp.status_code == 200:
            data = resp.json()
            # Send verification email
            v_url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={_config['apiKey']}"
            requests.post(v_url, json={"requestType": "VERIFY_EMAIL", "idToken": data["idToken"]})
            return True, "Account created! Check your email for verification link."
        else:
            err = resp.json().get("error", {}).get("message", "Unknown error")
            if "EMAIL_EXISTS" in err: return False, "Email already registered."
            return False, f"Error: {err}"
    except Exception as e:
        return False, str(e)

def login(email, password):
    global _user
    if not _config: return False, "Not initialized"
    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={_config['apiKey']}"
        resp = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
        if resp.status_code == 200:
            _user = resp.json()
            _save_session()
            return True, "Logged in!"
        else:
            err = resp.json().get("error", {}).get("message", "Unknown error")
            return False, "Wrong email or password."
    except Exception as e:
        return False, str(e)

def is_logged_in():
    return _user is not None

def get_email():
    return _user.get("email", "") if _user else ""

def get_uid():
    return _user.get("localId", "") if _user else ""

def logout():
    global _user
    _user = None
    if os.path.exists(SESSION_FILE):
        try: os.remove(SESSION_FILE)
        except: pass

def _db_url(path):
    base = _config.get("databaseURL", "").rstrip("/")
    return f"{base}/{path}.json?auth={_user['idToken']}"

def save_user_country(country):
    if not _user or not _config: return
    try:
        url = _db_url(f"users/{get_uid()}/settings")
        requests.patch(url, json={"home_country": country})
    except: pass

def get_user_country():
    if not _user or not _config: return None
    try:
        url = _db_url(f"users/{get_uid()}/settings/home_country")
        resp = requests.get(url)
        return resp.json() if resp.status_code == 200 else None
    except: return None

def cloud_save_news(saved_list):
    if not _user or not _config: return
    try:
        url = _db_url(f"users/{get_uid()}/saved_news")
        requests.put(url, json=saved_list)
    except: pass

def cloud_load_news():
    if not _user or not _config: return []
    try:
        url = _db_url(f"users/{get_uid()}/saved_news")
        resp = requests.get(url)
        if resp.status_code == 200:
            res = resp.json()
            if res is None: return []
            return list(res.values()) if isinstance(res, dict) else list(res)
    except: pass
    return []

def cloud_save_news_async(saved_list):
    threading.Thread(target=cloud_save_news, args=(saved_list,), daemon=True).start()
