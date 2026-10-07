# -*- coding: utf-8 -*-
"""設定項目の定義と、設定ファイル（JSON）の読み書き

- 設定画面（face_mouse_settings.py）と本体（face_mouse.py）の両方から使う
- 既定値は face_mouse.py 冒頭の定数を正とし、ここでは ast で読み取るだけにする
  （重い mediapipe 等を import せずに既定値を得るため。値の二重管理も避けられる）
- 設定ファイルには既定値から変更した項目だけでなく、保存時点の全項目を書き出す
"""

import ast
import json
import os
from pathlib import Path

# ============================================================
# パラメータ
# ============================================================

SCRIPTS_DIR = Path(__file__).resolve().parent
MAIN_SCRIPT_PATH = SCRIPTS_DIR / "face_mouse.py"
CONFIG_PATH = SCRIPTS_DIR / "face_mouse_config.json"

# タブの並び順
TABS = ["よく使う", "カーソル", "ウインク・クリック", "スクロール", "有効化・表示", "カメラ"]

# 「よく使う」タブに出す項目（他のタブと同じ値を共有する）
FAVORITE_KEYS = [
    "SENSITIVITY_X", "SENSITIVITY_Y", "EAR_CLOSED_THRESHOLD",
    "WINK_HOLD_SEC", "SCROLL_SPEED_GAIN", "OVERLAY_ALPHA",
]

# 設定項目の定義
#   key     : face_mouse.py の定数名
#   tab     : 表示するタブ
#   label   : 項目名
#   desc    : 説明（何をする値で、大きく／小さくするとどうなるか）
#   type    : "float" / "int" / "bool"
#   min/max/step : 数値の範囲と刻み（bool では不要）
#   restart : True なら起動時にしか読まない（保存後、顔マウスの再起動で反映）
SCHEMA = [
    # --- カーソル ---
    {"key": "SENSITIVITY_X", "tab": "カーソル", "label": "横方向の感度",
     "desc": "顔を左右に向けたときのカーソルの動きやすさ。大きいほど少しの首振りで大きく動く。",
     "type": "float", "min": 0.5, "max": 10.0, "step": 0.05},
    {"key": "SENSITIVITY_Y", "tab": "カーソル", "label": "縦方向の感度",
     "desc": "顔を上下に向けたときのカーソルの動きやすさ。縦の首振りは小さくなりがちなので横より大きめが目安。",
     "type": "float", "min": 0.5, "max": 10.0, "step": 0.05},
    {"key": "SMOOTHING_ALPHA", "tab": "カーソル", "label": "なめらかさ（平滑化係数）",
     "desc": "小さいほどカーソルの震えが減ってなめらかになるが、動きが遅れて付いてくる。",
     "type": "float", "min": 0.05, "max": 1.0, "step": 0.01},
    {"key": "DEAD_ZONE_PX", "tab": "カーソル", "label": "微小な動きを無視する距離（px）",
     "desc": "この距離未満のカーソル移動は無視する。止めたいのに小刻みに震えるときは大きくする。",
     "type": "int", "min": 0, "max": 30, "step": 1},
    {"key": "FREEZE_CURSOR_WHILE_WINK", "tab": "カーソル", "label": "ウインク中はカーソルを止める",
     "desc": "片目を閉じている間はカーソルを止め、クリック位置がずれないようにする。",
     "type": "bool"},

    # --- ウインク・クリック ---
    {"key": "EAR_CLOSED_THRESHOLD", "tab": "ウインク・クリック", "label": "目を閉じたとみなす値（EAR）",
     "desc": "目の開き具合（EAR）がこの値より小さいと「閉じている」と判定する。目を閉じても反応しないときは上げ、"
             "開けているのに閉じた判定になるときは下げる。実際の値は確認ウィンドウ（Ctrl+Alt+W）の左上で見られる。",
     "type": "float", "min": 0.05, "max": 0.30, "step": 0.005},
    {"key": "WINK_EAR_DIFF", "tab": "ウインク・クリック", "label": "ウインク開始に必要な左右差",
     "desc": "閉じた目と開いた目のEARの差がこれ以上でウインクとみなす。ウインクが認識されにくいときは小さくする。",
     "type": "float", "min": 0.0, "max": 0.20, "step": 0.005},
    {"key": "WINK_KEEP_EAR_DIFF", "tab": "ウインク・クリック", "label": "ウインク継続に必要な左右差",
     "desc": "ウインク中に反対の目がつられて細くなっても途切れないよう、開始より緩い差で継続を判定する。",
     "type": "float", "min": 0.0, "max": 0.20, "step": 0.005},
    {"key": "WINK_HOLD_SEC", "tab": "ウインク・クリック", "label": "クリックに必要なウインク時間（秒）",
     "desc": "片目をこの秒数以上閉じてから開けるとクリック。誤クリックが多いときは長くする。",
     "type": "float", "min": 0.1, "max": 1.5, "step": 0.05},
    {"key": "DOUBLE_CLICK_HOLD_SEC", "tab": "ウインク・クリック", "label": "ダブルクリックまでの時間（秒）",
     "desc": "左目をこの秒数閉じ続けるとダブルクリック。これより短く開ければ左クリック。",
     "type": "float", "min": 0.5, "max": 3.0, "step": 0.1},
    {"key": "CLICK_COOLDOWN_SEC", "tab": "ウインク・クリック", "label": "クリック後の待ち時間（秒）",
     "desc": "クリックしてからこの秒数は次のクリックを受け付けない（連続誤クリック防止）。",
     "type": "float", "min": 0.0, "max": 3.0, "step": 0.1},

    # --- スクロール ---
    {"key": "SCROLL_HOLD_SEC", "tab": "スクロール", "label": "スクロール保持を始める時間（秒）",
     "desc": "右目をこの秒数閉じ続けるとスクロール保持モードになる。これより短く開ければ右クリック。",
     "type": "float", "min": 0.5, "max": 5.0, "step": 0.1},
    {"key": "SCROLL_SPEED_GAIN", "tab": "スクロール", "label": "スクロールの速さ",
     "desc": "顔を上下に向けた量に対するスクロールの速さ。速すぎるときは小さく、遅すぎるときは大きくする。",
     "type": "float", "min": 10.0, "max": 1000.0, "step": 10.0},
    {"key": "SCROLL_MAX_NOTCHES_PER_SEC", "tab": "スクロール", "label": "スクロール速度の上限（段/秒）",
     "desc": "大きく顔を向けたときでも、1秒あたりこのホイール段数より速くはスクロールしない。",
     "type": "float", "min": 1.0, "max": 60.0, "step": 1.0},
    {"key": "SCROLL_DEAD_ZONE", "tab": "スクロール", "label": "スクロールしない範囲",
     "desc": "スクロール開始時の顔の高さからこの範囲内ではスクロールしない。正面を向いても止まらないときは大きくする。",
     "type": "float", "min": 0.0, "max": 0.10, "step": 0.005},

    # --- 有効化・表示 ---
    {"key": "ACTIVATE_HOLD_SEC", "tab": "有効化・表示", "label": "有効にするまでの時間（秒）",
     "desc": "無効のとき、両目をこの秒数閉じ続けると有効になる。",
     "type": "float", "min": 0.5, "max": 5.0, "step": 0.1},
    {"key": "DEACTIVATE_HOLD_SEC", "tab": "有効化・表示", "label": "無効に戻すまでの時間（秒）",
     "desc": "有効のとき、両目をこの秒数閉じ続けると無効に戻る。有効にする時間より長くしておくと誤操作しにくい。",
     "type": "float", "min": 1.0, "max": 10.0, "step": 0.1},
    {"key": "START_PAUSED", "tab": "有効化・表示", "label": "起動直後は無効にする",
     "desc": "オンなら起動直後は無効（誤操作防止）。オフなら起動直後から有効。",
     "type": "bool", "restart": True},
    {"key": "OVERLAY_ALPHA", "tab": "有効化・表示", "label": "画面上部の状態表示の濃さ",
     "desc": "画面上部中央の状態表示の不透明度。小さいほど薄くなる。",
     "type": "float", "min": 0.1, "max": 1.0, "step": 0.05},
    {"key": "SHOW_STATUS_OVERLAY", "tab": "有効化・表示", "label": "画面上部に状態を表示する",
     "desc": "オフにすると画面上部中央の状態表示を出さない。",
     "type": "bool", "restart": True},
    {"key": "SHOW_WINDOW_ON_START", "tab": "有効化・表示", "label": "起動時に確認ウィンドウを表示する",
     "desc": "オンなら起動時からカメラ映像の確認ウィンドウを出す（Ctrl+Alt+W でいつでも切り替え可能）。",
     "type": "bool", "restart": True},

    # --- カメラ ---
    {"key": "CAMERA_INDEX", "tab": "カメラ", "label": "使用するカメラ番号",
     "desc": "内蔵カメラは通常0。外付けカメラを使うときは1などに変える。",
     "type": "int", "min": 0, "max": 9, "step": 1, "restart": True},
]

SCHEMA_BY_KEY = {item["key"]: item for item in SCHEMA}


def load_defaults():
    """face_mouse.py 冒頭の定数から、設定項目の既定値を読み取る

    face_mouse.py を import せず ast で解析する（mediapipe 等の重い import を避けるため）。
    """
    try:
        source = MAIN_SCRIPT_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(MAIN_SCRIPT_PATH))
    except (OSError, SyntaxError) as e:
        print("既定値を読み取れませんでした: {} ({})".format(MAIN_SCRIPT_PATH, e))
        raise

    defaults = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in SCHEMA_BY_KEY:
            continue
        try:
            defaults[target.id] = ast.literal_eval(node.value)
        except ValueError:
            # 式で書かれた定数は既定値として扱えない（設定項目には定数リテラルのみを使う）
            print("注意: {} の既定値が定数ではないため読み取れません。".format(target.id))

    missing = [item["key"] for item in SCHEMA if item["key"] not in defaults]
    if missing:
        raise ValueError("face_mouse.py に設定項目の定数が見つかりません: {}".format(", ".join(missing)))
    # 設定画面で比較しやすいよう、既定値も型・刻みをそろえておく
    return {key: normalize_value(key, value) for key, value in defaults.items()}


def normalize_value(key, value):
    """設定値を項目の型・範囲に合わせて変換する。扱えない値なら ValueError"""
    item = SCHEMA_BY_KEY[key]
    if item["type"] == "bool":
        if isinstance(value, bool):
            return value
        raise ValueError("真偽値ではありません: {!r}".format(value))
    if isinstance(value, bool):
        # True/False は int の一種なので、数値項目では明示的に弾く
        raise ValueError("数値ではありません: {!r}".format(value))
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("数値ではありません: {!r}".format(value))
    number = min(max(number, item["min"]), item["max"])
    if item["type"] == "int":
        return int(round(number))
    # 刻みに合わせて丸め、浮動小数点の誤差（0.30000000000000004 など）を消す
    step = item["step"]
    number = round(round(number / step) * step, 6)
    return number


def load_config(path=None):
    """設定ファイルを読み、有効な項目だけを {定数名: 値} で返す（ファイルが無ければ空）

    未知の項目・不正な値は無視して、その旨を表示する（読める項目は使う）。
    """
    path = Path(path) if path is not None else CONFIG_PATH
    if not path.exists():
        return {}
    try:
        with open(str(path), "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        print("設定ファイルを読み込めませんでした（既定値で動作します）: {} ({})".format(path, e))
        return {}
    if not isinstance(data, dict):
        print("設定ファイルの形式が正しくありません（既定値で動作します）: {}".format(path))
        return {}

    values = {}
    for key, value in data.items():
        if key not in SCHEMA_BY_KEY:
            print("注意: 設定ファイルの未知の項目を無視します: {}".format(key))
            continue
        try:
            values[key] = normalize_value(key, value)
        except (TypeError, ValueError) as e:
            print("注意: 設定ファイルの {} の値が不正なため無視します（{}）".format(key, e))
    return values


def save_config(values, path=None):
    """設定ファイルに書き出す（一時ファイルに書いてから置き換え、途中で壊れないようにする）"""
    path = Path(path) if path is not None else CONFIG_PATH
    data = {item["key"]: values[item["key"]] for item in SCHEMA if item["key"] in values}
    tmp_path = path.with_name(path.name + ".tmp")
    try:
        with open(str(tmp_path), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(str(tmp_path), str(path))
    except OSError as e:
        print("設定ファイルを保存できませんでした: {} ({})".format(path, e))
        raise
