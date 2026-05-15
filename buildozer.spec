[app]
title = NewsIn
package.name = newsin
package.domain = org.newsin
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json,ttf
version = 1.0.0
requirements = python3,pygame,requests,feedparser==6.0.10,urllib3,chardet,certifi,idna,sqlite3,openssl,sdl2_image,sdl2_mixer,sdl2_ttf,sdl2,pyrebase4,gTTS,deep-translator,plyer,google-generativeai

orientation = portrait
fullscreen = 1
android.permissions = INTERNET, WAKE_LOCK, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE, RECORD_AUDIO
android.api = 33
android.minapi = 21
android.ndk = 25b
android.sdk = 33
android.accept_sdk_license = True

# (str) The Android arch to build for, choices: armeabi-v7a, arm64-v8a, x86, x86_64
android.archs = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1
