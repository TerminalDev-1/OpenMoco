"""Resolve Android tooling without publishing workstation-specific paths."""
import os
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
LOCAL_APP_DATA = Path(os.environ.get('LOCALAPPDATA', str(Path.home())))
sdk_config = ROOT / '.local' / 'android-sdk.txt'
sdk_setting = os.environ.get('ANDROID_SDK_ROOT') or os.environ.get('ANDROID_HOME')
if not sdk_setting and sdk_config.is_file():
    sdk_setting = sdk_config.read_text(encoding='utf-8-sig').strip()
SDK = Path(sdk_setting) if sdk_setting else LOCAL_APP_DATA / 'Android' / 'Sdk'
BUILD_TOOLS = SDK / 'build-tools' / '35.0.0'
adb_name = 'adb.exe' if os.name == 'nt' else 'adb'
adb_candidates = [SDK / 'platform-tools' / adb_name,
                  LOCAL_APP_DATA / 'Android' / 'platform-tools' / adb_name]
DEFAULT_ADB = Path(shutil.which('adb') or next(
    (str(path) for path in adb_candidates if path.is_file()), str(adb_candidates[0])))
