[app]
title = NewsIn
package.name = newsin
package.domain = org.newsin
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 1.0.0
requirements = python3,pygame,requests,feedparser,deep-translator,gTTS,urllib3,chardet,certifi,idna,six,pyrebase4,pycryptodome,python-jwt,gcloud,requests-toolbelt

orientation = portrait
fullscreen = 1
android.permissions = INTERNET, WAKE_LOCK, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE

# (str) Icon of the application
# icon.filename = %(source.dir)s/icon.png

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/presplash.png

android.api = 31
android.minapi = 21
android.ndk = 25b
android.sdk = 33

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
