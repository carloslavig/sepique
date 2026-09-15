#!/usr/bin/env python3
"""Reaplica os patches manuais feitos no checkout local do
python-for-android (dentro de .buildozer/, que fica fora do git e é
recriado do zero sempre que o cache é limpo).

Rodar de dentro do WSL depois de qualquer `buildozer android debug` que
tenha reclonado o python-for-android, ANTES do build (ou relançar o build
depois de rodar isso). Idempotente: pode rodar várias vezes sem problema.

Uso:
    python3 scripts/patch_p4a.py /root/sepique/.buildozer/android/platform/python-for-android
"""
import sys
from pathlib import Path


def patch_pip_version(build_py: Path) -> None:
    text = build_py.read_text()
    old = "source venv/bin/activate && pip install -U pip"
    new = "source venv/bin/activate && pip install 'pip==24.3.1'"
    if new in text:
        print("[pip version] ja aplicado")
        return
    if old not in text:
        print("[pip version] ATENCAO: trecho original nao encontrado, pulei")
        return
    build_py.write_text(text.replace(old, new))
    print("[pip version] aplicado")


def patch_pip_platform_flags(build_py: Path) -> None:
    text = build_py.read_text()
    marker = "platform_tag = 'android_'"
    if marker in text:
        print("[pip platform flags] ja aplicado")
        return
    old = '''            shprint(sh.bash, '-c', (
                "venv/bin/pip " +
                "install -v --target '{0}' --no-deps -r requirements.txt"
            ).format(ctx.get_site_packages_dir(arch).replace("'", "'\\"'\\"'")),
                    _env=copy.copy(env))'''
    new = '''            py_ver = ctx.python_recipe.major_minor_version_string
            abi_tag = 'cp' + py_ver.replace('.', '')
            platform_tag = 'android_' + str(ctx.ndk_api) + '_' + arch.arch.replace('-', '_')
            shprint(sh.bash, '-c', (
                "venv/bin/pip " +
                "install -v --target '{0}' --no-deps "
                "--platform " + platform_tag + " --implementation cp "
                "--python-version " + py_ver + " --abi " + abi_tag + " "
                "-r requirements.txt"
            ).format(ctx.get_site_packages_dir(arch).replace("'", "'\\"'\\"'")),
                    _env=copy.copy(env))'''
    if old not in text:
        print("[pip platform flags] ATENCAO: trecho original nao encontrado, pulei")
        return
    build_py.write_text(text.replace(old, new))
    print("[pip platform flags] aplicado")


def patch_manifest_service(manifest_tmpl: Path) -> None:
    text = manifest_tmpl.read_text()
    if "RideOfferAccessibilityService" in text:
        print("[manifest service] ja aplicado")
        return
    anchor = """        {% if service or args.launcher %}
        <service android:name="{{ args.service_class_name }}"
                 android:process=":pythonservice" />
        {% endif %}"""
    service_block = (
        '''        <service
            android:name="com.lavigne.sepique.RideOfferAccessibilityService"
            android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"
            android:exported="true">
            <intent-filter>
                <action android:name="android.accessibilityservice.AccessibilityService" />
            </intent-filter>
            <meta-data
                android:name="android.accessibilityservice.config"
                android:resource="@xml/accessibility_service_config" />
        </service>

'''
        + anchor
    )
    if anchor not in text:
        print("[manifest service] ATENCAO: trecho original nao encontrado, pulei")
        return
    manifest_tmpl.write_text(text.replace(anchor, service_block))
    print("[manifest service] aplicado")


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    p4a_dir = Path(sys.argv[1])
    build_py = p4a_dir / "pythonforandroid" / "build.py"
    manifest_tmpl = (
        p4a_dir
        / "pythonforandroid"
        / "bootstraps"
        / "_sdl_common"
        / "build"
        / "templates"
        / "AndroidManifest.tmpl.xml"
    )
    if not build_py.exists() or not manifest_tmpl.exists():
        print("Nao achei os arquivos esperados dentro de", p4a_dir)
        sys.exit(1)
    patch_pip_version(build_py)
    patch_pip_platform_flags(build_py)
    patch_manifest_service(manifest_tmpl)


if __name__ == "__main__":
    main()
