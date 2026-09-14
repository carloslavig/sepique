[app]
title = Se Pique
package.name = sepique
package.domain = com.lavigne

source.dir = .
source.include_exts = py,png,jpg,kv,atlas

version = 0.1.0
requirements = python3,kivy,cython==0.29.36,plyer

orientation = portrait
fullscreen = 0

android.permissions = ACCESS_FINE_LOCATION,ACCESS_COARSE_LOCATION,INTERNET
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a
android.accept_sdk_license = True
android.build_tools = 34.0.0
android.sdk_path = /usr/local/lib/android/sdk

[buildozer]
log_level = 2
warn_on_root = 1
