[app]
title = Corretor de Simulado
package.name = corretorsimulado
package.domain = org.corretor

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas
version = 0.1

# numpy e opencv são pesados: o primeiro build pode levar 30-60+ min.
requirements = python3,kivy==2.3.0,plyer,numpy,opencv,pillow

orientation = portrait
fullscreen = 0

# Descomente e adicione um icon.png (512x512) na raiz do projeto se quiser um ícone customizado.
# icon.filename = %(source.dir)s/icon.png

android.permissions = CAMERA,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.allow_backup = True

# Necessário pois plyer.camera abre o app nativo de câmera via intent.
android.add_activities =

[buildozer]
log_level = 2
warn_on_root = 1
