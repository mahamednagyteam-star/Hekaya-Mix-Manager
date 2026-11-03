[app]
title = Hekaya Mix Manager
package.name = hekayamixmanager
package.domain = com.mahamednagyteam
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 3.0.0
requirements = python3,kivy,requests,colorama,arabic-reshaper,python-bidi
orientation = portrait
fullscreen = 0
android.api = 33
android.minapi = 23
android.archs = arm64-v8a
android.permissions = INTERNET
android.allow_backup = False
android.ndk = 25b
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 0
