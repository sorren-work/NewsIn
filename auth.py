"""
Firebase Authentication & Cloud Sync for NewsIn.
Handles login, register, email verification, and saved news sync.
"""
import json, os, threading

FIREBASE_CONFIG_FILE = "firebase_config.json"
SESSION_FILE = "session.json"

_firebase = None
_auth = None
_db = None
_user = None  # Current logged-in user token
_user_info = None  # User profile info

def _load_config():
    if os.path.exists(FIREBASE_CONFIG_FILE):
        with open(FIREBASE_CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

def _save_session():
    """Save login session locally so user doesn't have to login again."""
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
    """Try to restore a saved login session."""
    global _user, _user_info
    if not _auth or not os.path.exists(SESSION_FILE):
        return False
    try:
        with open(SESSION_FILE, "r") as f:
            session = json.load(f)
        # Try to refresh the token
        refreshed = _auth.refresh(session.get("refreshToken", ""))
        _user = {
            "idToken": refreshed["idToken"],
            "refreshToken": refreshed["refreshToken"],
            "localId": refreshed.get("userId", session.get("localId", "")),
            "email": session.get("email", ""),
        }
        _user_info = _auth.get_account_info(_user["idToken"])
        return True
    except Exception as e:
        print(f"Session restore failed: {e}")
        # Delete invalid session
        try: os.remove(SESSION_FILE)
        except: pass
        return False

def _clear_session():
    """Remove saved session file."""
    try:
        if os.path.exists(SESSION_FILE):
            os.remove(SESSION_FILE)
    except: pass

def init():
    """Initialize Firebase connection."""
    global _firebase, _auth, _db
    config = _load_config()
    if not config:
        print("Firebase config not found!")
        return False
    try:
        import pyrebase
        _firebase = pyrebase.initialize_app(config)
        _auth = _firebase.auth()
        _db = _firebase.database()
        return True
    except Exception as e:
        print(f"Firebase init error: {e}")
        return False

def try_auto_login():
    """Try to automatically log in from saved session. Returns True if successful."""
    return _load_session()

def register(email, password):
    """Register a new user. Returns (success, message)."""
    if not _auth:
        return False, "Firebase not initialized"
    try:
        user = _auth.create_user_with_email_and_password(email, password)
        # Send email verification
        _auth.send_email_verification(user['idToken'])
        return True, "Account created! Check your email for verification link."
    except Exception as e:
        err = str(e)
        if "EMAIL_EXISTS" in err:
            return False, "This email is already registered."
        elif "WEAK_PASSWORD" in err:
            return False, "Password must be at least 6 characters."
        elif "INVALID_EMAIL" in err:
            return False, "Please enter a valid email address."
        return False, f"Registration failed: {err[:80]}"

def login(email, password):
    """Log in a user. Returns (success, message)."""
    global _user, _user_info
    if not _auth:
        return False, "Firebase not initialized"
    try:
        user = _auth.sign_in_with_email_and_password(email, password)
        _user = user
        _user_info = _auth.get_account_info(user['idToken'])
        _save_session()  # Remember the login!
        return True, "Logged in!"
    except Exception as e:
        err = str(e)
        if "INVALID_LOGIN_CREDENTIALS" in err or "INVALID_PASSWORD" in err:
            return False, "Wrong email or password."
        elif "EMAIL_NOT_FOUND" in err:
            return False, "No account found with this email."
        elif "TOO_MANY_ATTEMPTS" in err:
            return False, "Too many attempts. Try again later."
        return False, f"Login failed: {err[:80]}"

def is_logged_in():
    return _user is not None

def get_email():
    if _user:
        return _user.get("email", "")
    return ""

def get_uid():
    if _user:
        return _user.get("localId", "")
    return ""

def logout():
    global _user, _user_info
    _user = None
    _user_info = None
    _clear_session()

# ── Cloud Sync ─────────────────────────────────────────────────────────────────

def save_user_country(country):
    """Save user's home country to cloud."""
    if not _db or not _user:
        return
    try:
        _db.child("users").child(get_uid()).child("settings").update(
            {"home_country": country}, _user['idToken'])
    except Exception as e:
        print(f"Cloud save country error: {e}")

def get_user_country():
    """Get user's home country from cloud."""
    if not _db or not _user:
        return None
    try:
        data = _db.child("users").child(get_uid()).child("settings").child("home_country").get(_user['idToken'])
        return data.val()
    except:
        return None

def cloud_save_news(saved_list):
    """Upload saved news list to cloud."""
    if not _db or not _user:
        return
    try:
        _db.child("users").child(get_uid()).child("saved_news").set(
            saved_list, _user['idToken'])
    except Exception as e:
        print(f"Cloud save error: {e}")

def cloud_load_news():
    """Download saved news list from cloud."""
    if not _db or not _user:
        return []
    try:
        data = _db.child("users").child(get_uid()).child("saved_news").get(_user['idToken'])
        result = data.val()
        if result is None:
            return []
        if isinstance(result, dict):
            return list(result.values())
        return list(result)
    except Exception as e:
        print(f"Cloud load error: {e}")
        return []

def cloud_save_news_async(saved_list):
    """Save news in background thread."""
    threading.Thread(target=cloud_save_news, args=(saved_list,), daemon=True).start()
