[app]
title = Se Pique
package.name = sepique
package.domain = com.lavigne

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 0.1.0
requirements = python3,kivy,plyer

orientation = portrait
fullscreen = 0

android.permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,INTERNET,SYSTEM_ALERT_WINDOW
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True
android.build_tools = 34.0.0
android.sdk_path = /usr/local/lib/android/sdk
android.add_src = android-extra/src
android.add_resources = android-extra/res

[buildozer]
log_level = 2
warn_on_root = 1
