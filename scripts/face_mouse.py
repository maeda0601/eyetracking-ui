# -*- coding: utf-8 -*-
"""顔の向きとウインクでマウスを操作するツール

Webカメラの映像から MediaPipe Face Landmarker で顔のランドマークを検出し、
- 鼻先の位置（起動時の位置からの移動量）でカーソルを動かす
- 左目だけのウインクで左クリック（1秒以上続けるとダブルクリック）
- 右目だけのウインクで右クリック（2秒以上続けるとスクロール保持モード）
を行う。
スクロール保持モード中はカーソルを止め、顔を上下に向けるとスクロールする。
もう一度ウインク（左右どちらでも）すると解除する。
起動直後は無効（一時停止）状態で、両目を2秒閉じると有効になる。
有効中に両目を5秒閉じると無効に戻る。

確認ウィンドウ（カメラ映像）は起動時には表示しない。Ctrl+Alt+W で表示／非表示を切り替える。
起動中は画面上部中央に、半透明の小さな状態表示（オーバーレイ）を常に出す。

キー操作（確認ウィンドウ表示中、かつアクティブなときのみ有効）:
    p       : 一時停止／再開
    c       : 現在の顔の位置を中心として再設定（キャリブレーション）
    q / ESC : 終了

グローバルホットキー（Windowsのみ。ウィンドウの有無・フォーカスに関係なく有効）:
    Ctrl+Alt+P : 一時停止／再開
    Ctrl+Alt+C : 現在の顔の位置を中心として再設定
    Ctrl+Alt+W : 確認ウィンドウの表示／非表示
    Ctrl+Alt+Q : 終了
"""

import ctypes
import sys
import time
from pathlib import Path

try:
    import tkinter as tk
except ImportError:
    # 組み込み版Pythonなど tkinter が無い環境では、状態表示（オーバーレイ）なしで動かす
    tk = None

import cv2
import mediapipe as mp
import pyautogui
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision

# ============================================================
# パラメータ（環境に合わせてここを調整する）
# ============================================================

# --- カメラ ---
CAMERA_INDEX = 0                # 使用するカメラ番号（内蔵カメラは通常0）
FRAME_WIDTH = 640               # 取得する映像の幅
FRAME_HEIGHT = 480              # 取得する映像の高さ

# --- モデル ---
# Face Landmarker のモデルファイル。ネットワーク制限環境を想定し、事前に配置しておく
MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "face_landmarker.task"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
             "face_landmarker/float16/1/face_landmarker.task")

# --- カーソル移動 ---
SENSITIVITY_X = 3.0             # 横方向の感度（大きいほど少ない首振りで大きく動く）
SENSITIVITY_Y = 3.75            # 縦方向の感度（縦の首振りは小さくなりがちなので横より大きめ）
SMOOTHING_ALPHA = 0.25          # 指数平滑化の係数（0〜1。小さいほど滑らかだが遅れる）
DEAD_ZONE_PX = 4                # この距離(px)未満の移動は無視する（微小なブレ対策）
SCREEN_MARGIN_PX = 3            # 画面端から離す距離(px)。ツール自身がFAILSAFEを発動させないため
FREEZE_CURSOR_WHILE_WINK = True # 片目を閉じている間はカーソルを止める（クリック位置のズレ防止）

# --- ウインク判定（EAR: Eye Aspect Ratio） ---
# ※実測では開いた目が約0.22、閉じた目が約0.09。人やカメラ位置で変わるため、画面のEAR表示を見て調整する
EAR_CLOSED_THRESHOLD = 0.14     # これ未満なら「目を閉じている」とみなす
# ウインク中は反対の目もつられて細くなりやすいため、反対の目は絶対値ではなく
# 「閉じた目よりどれだけ開いているか（EARの差）」で判定する。
# 両目のまばたきは左右がほぼ同じ値まで下がるので、差が小さく自動的に除外される
WINK_EAR_DIFF = 0.05            # ウインク開始に必要な左右のEAR差
WINK_KEEP_EAR_DIFF = 0.03       # ウインク継続中に必要な左右のEAR差（開始より緩くして途切れを防ぐ）
WINK_HOLD_SEC = 0.3             # ウインクがこの秒数続いたらクリック確定
DOUBLE_CLICK_HOLD_SEC = 1.0     # 左ウインクがこの秒数続いたらダブルクリック
SCROLL_HOLD_SEC = 2.0           # 右ウインクがこの秒数続いたらスクロール保持モードを開始
CLICK_COOLDOWN_SEC = 1.0        # クリック後、次のクリックを受け付けるまでの秒数

# --- スクロール保持モード ---
# 開始時の鼻先の高さを基準に、顔を上下に向けた量に応じてスクロールする
SCROLL_DEAD_ZONE = 0.015        # この量（映像の高さに対する割合）未満の上下の動きではスクロールしない
SCROLL_SPEED_GAIN = 200.0       # 速度の係数（デッドゾーンを超えた量 × 係数 = 1秒あたりのホイール段数）
SCROLL_MAX_NOTCHES_PER_SEC = 20.0  # スクロール速度の上限（1秒あたりのホイール段数）
# ホイール1段分の量。Windows では pyautogui.scroll の値がそのままホイール量として送られ、120 が1段
WHEEL_DELTA = 120 if sys.platform.startswith("win") else 1

# --- 有効化（起動時は無効状態） ---
START_PAUSED = True             # True なら起動直後は無効（一時停止）状態にする
ACTIVATE_HOLD_SEC = 2.0         # 無効状態で両目をこの秒数閉じ続けると有効になる
DEACTIVATE_HOLD_SEC = 5.0       # 有効状態で両目をこの秒数閉じ続けると無効に戻る
EYES_CLOSED_MSG_DELAY_SEC = 0.5 # 両目をこの秒数以上閉じたら経過時間を表示する（まばたきで表示がちらつかないため）

# --- 表示 ---
WINDOW_NAME = "Face Mouse"      # 確認ウィンドウ名（OpenCVは日本語表示に非対応のため英字）
# 起動時に確認ウィンドウを表示するか。False でも Ctrl+Alt+W で表示できる
# ※Windows以外ではグローバルホットキーが使えず操作できなくなるため、常に表示する
SHOW_WINDOW_ON_START = False

# --- 状態表示（画面上部中央のオーバーレイ） ---
SHOW_STATUS_OVERLAY = True      # 起動中であることが分かるよう、画面上部中央に状態を常時表示する
OVERLAY_ALPHA = 0.55            # 不透明度（0〜1。小さいほど薄い）
OVERLAY_FONT = ("Meiryo UI", 10)
OVERLAY_TOP_PX = 2              # 画面上端からの距離(px)
OVERLAY_BG = "#202020"          # 背景色（どんな壁紙の上でも文字が読めるよう暗い背景を敷く）
OVERLAY_COLORS = {              # 状態ごとの文字色
    "active": "#9be09b",
    "paused": "#d0d0d0",
    "no_face": "#f0a0a0",
}
SHOW_ALL_LANDMARKS = False      # True で顔全体のランドマークを描画（重くなる場合あり）

# --- グローバルホットキー（Windowsのみ） ---
# 確認ウィンドウが裏に回っても操作できるよう、OSからキー状態を直接読む。
# 値は Windows の仮想キーコード（VK_*）。他アプリと重なる場合はここを変更する
VK_CONTROL = 0x11
VK_MENU = 0x12                  # Altキー
HOTKEY_MODIFIERS = (VK_CONTROL, VK_MENU)   # Ctrl+Alt
# (キー, 操作名) の組。同時に押された場合は先頭に近いものを優先する
HOTKEY_ACTIONS = (
    (ord("Q"), "quit"),         # Ctrl+Alt+Q : 終了
    (ord("P"), "pause"),        # Ctrl+Alt+P : 一時停止／再開
    (ord("C"), "center"),       # Ctrl+Alt+C : 中心の再設定
    (ord("W"), "window"),       # Ctrl+Alt+W : 確認ウィンドウの表示／非表示
)

# ============================================================
# ランドマーク番号（MediaPipe Face Mesh 478点の定義）
# ============================================================

NOSE_TIP = 1
# EAR計算用の6点 [目尻/目頭, 上1, 上2, 目頭/目尻, 下2, 下1]
# ※「左目」「右目」は本人から見た左右（カメラ映像上では左右が逆に映る）
LEFT_EYE_POINTS = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_POINTS = [33, 160, 158, 133, 153, 144]

# ============================================================
# pyautogui の設定
# ============================================================

# FAILSAFE は有効のままにする。
# 実際のマウスを画面の四隅のいずれかに動かすと pyautogui.FailSafeException が発生し、
# 誤作動時でもツールを緊急停止できる。安全のため False にしないこと。
pyautogui.FAILSAFE = True
# 既定では pyautogui の各操作後に0.1秒待機が入り、カーソルがカクつくため0にする
pyautogui.PAUSE = 0


def calc_distance(p1, p2):
    """2点間のユークリッド距離を返す"""
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def calc_ear(landmarks, indices, frame_w, frame_h):
    """指定した目のEAR（Eye Aspect Ratio）を計算する

    EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
    目を開けていると大きく、閉じると0に近づく。
    正規化座標のままだと縦横比が歪むため、ピクセル座標に変換して計算する。
    """
    pts = [(landmarks[i].x * frame_w, landmarks[i].y * frame_h) for i in indices]
    vertical = calc_distance(pts[1], pts[5]) + calc_distance(pts[2], pts[4])
    horizontal = calc_distance(pts[0], pts[3])
    if horizontal == 0:
        return 0.0
    return vertical / (2.0 * horizontal)


class WinkDetector:
    """左右のEARからウインクを判定し、実行すべき操作を返す

    左右とも長さで操作を分けるため、短いウインクは目を開けた時点で判定する
    - 左ウインク:
        WINK_HOLD_SEC 以上 DOUBLE_CLICK_HOLD_SEC 未満で開けた → 左クリック（"left"）
        DOUBLE_CLICK_HOLD_SEC 続いた時点 → ダブルクリック（"double"。開けるのを待たずに確定）
    - 右ウインク:
        WINK_HOLD_SEC 以上 SCROLL_HOLD_SEC 未満で開けた → 右クリック（"right"）
        SCROLL_HOLD_SEC 続いた時点 → スクロール保持モードの開始（"scroll"）
    """

    # 短いウインク（開けた時点で確定）と長いウインク（一定時間で確定）の操作名
    SHORT_ACTION = {"left": "left", "right": "right"}
    LONG_ACTION = {"left": "double", "right": "scroll"}

    def __init__(self):
        self.wink_start = {"left": None, "right": None}  # ウインク開始時刻
        self.last_seen = {"left": None, "right": None}   # ウインクを最後に確認した時刻
        self.fired = {"left": False, "right": False}     # このウインクでクリック済みか
        self.last_click_time = float("-inf")  # 起動直後はクールダウンなし

    def reset(self):
        """判定状態を初期化する（顔を見失ったときや一時停止時）"""
        self.wink_start = {"left": None, "right": None}
        self.last_seen = {"left": None, "right": None}
        self.fired = {"left": False, "right": False}

    def get_hold_time(self, side, now):
        """指定した側のウインク継続時間（秒）。ウインク中でなければ0"""
        if self.wink_start[side] is None:
            return 0.0
        return now - self.wink_start[side]

    def _fire(self, side, now):
        """クリックを確定し、クールダウンを開始する"""
        self.fired[side] = True
        self.last_click_time = now

    def start_cooldown(self, now):
        """クールダウンだけを開始する（有効化直後に目を開ける動作で誤クリックしないため）"""
        self.last_click_time = now

    @staticmethod
    def long_hold_sec(side):
        """長いウインクと判定するまでの秒数"""
        return DOUBLE_CLICK_HOLD_SEC if side == "left" else SCROLL_HOLD_SEC

    def update(self, ear_left, ear_right, now):
        """EARを受け取り、実行すべき操作（"left" / "double" / "right" / "scroll"）または None を返す"""
        def is_winking(side, ear_self, ear_other):
            # ウインク継続中は差の条件を緩める（ヒステリシス）
            required = WINK_KEEP_EAR_DIFF if self.wink_start[side] is not None else WINK_EAR_DIFF
            return ear_self < EAR_CLOSED_THRESHOLD and (ear_other - ear_self) >= required

        # 左ウインク：左目を閉じ、右目が左目より十分に開いている（右も同様）
        # 両目のまばたきは差が小さいため、どちらも False になり無視される
        states = {
            "left": is_winking("left", ear_left, ear_right),
            "right": is_winking("right", ear_right, ear_left),
        }

        # 両目とも閉じた（まばたき、またはウインク中に反対の目も閉じた）場合は
        # 計測を取り消し、クリックしない
        both_closed = ear_left < EAR_CLOSED_THRESHOLD and ear_right < EAR_CLOSED_THRESHOLD
        if both_closed and not any(states.values()):
            self.reset()
            return None

        in_cooldown = (now - self.last_click_time) < CLICK_COOLDOWN_SEC
        result = None
        for side, winking in states.items():
            if not winking:
                # 目を開けた時点で、長いウインク未満の長さなら短いウインクの操作（クリック）
                if (self.wink_start[side] is not None
                        and not self.fired[side] and not in_cooldown):
                    held = self.last_seen[side] - self.wink_start[side]
                    if held >= WINK_HOLD_SEC:
                        self._fire(side, now)
                        result = self.SHORT_ACTION[side]
                # 目を開けたらリセットし、次のウインクを受け付ける
                self.wink_start[side] = None
                self.last_seen[side] = None
                self.fired[side] = False
                continue

            if self.wink_start[side] is None:
                self.wink_start[side] = now
            self.last_seen[side] = now
            held = now - self.wink_start[side]
            if self.fired[side] or in_cooldown:
                continue
            if held >= self.long_hold_sec(side):
                self._fire(side, now)
                result = self.LONG_ACTION[side]
        return result

    def is_any_eye_closing(self):
        """どちらかの目でウインクを計測中かどうか"""
        return any(t is not None for t in self.wink_start.values())


class CursorController:
    """鼻先の位置を画面座標に変換し、平滑化・デッドゾーン処理をしてカーソルを動かす"""

    def __init__(self, screen_w, screen_h):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.center = None       # 基準となる鼻先の正規化座標
        self.smoothed = None     # 平滑化後のカーソル目標位置
        self.last_moved = None   # 最後に実際にカーソルを動かした位置

    def calibrate(self, nose_x, nose_y):
        """現在の鼻先位置を中心として設定し、カーソルを画面中央に置く"""
        self.center = (nose_x, nose_y)
        self.smoothed = (self.screen_w / 2.0, self.screen_h / 2.0)
        self.last_moved = None

    def update(self, nose_x, nose_y, freeze=False):
        """鼻先の正規化座標からカーソルを移動する"""
        if self.center is None:
            self.calibrate(nose_x, nose_y)

        # カメラ映像は鏡像ではないため、本人が右を向くと鼻先は映像の左へ動く。
        # 符号を反転して「右を向く→カーソルが右へ」となるようにする
        dx = -(nose_x - self.center[0])
        dy = nose_y - self.center[1]
        target_x = self.screen_w / 2.0 + dx * self.screen_w * SENSITIVITY_X
        target_y = self.screen_h / 2.0 + dy * self.screen_h * SENSITIVITY_Y

        # 画面外に出ないよう制限（四隅に触れてFAILSAFEが誤発動しないよう余白を取る）
        target_x = min(max(target_x, SCREEN_MARGIN_PX), self.screen_w - 1 - SCREEN_MARGIN_PX)
        target_y = min(max(target_y, SCREEN_MARGIN_PX), self.screen_h - 1 - SCREEN_MARGIN_PX)

        if freeze:
            return

        # 指数平滑化
        sx, sy = self.smoothed
        sx += SMOOTHING_ALPHA * (target_x - sx)
        sy += SMOOTHING_ALPHA * (target_y - sy)
        self.smoothed = (sx, sy)

        # デッドゾーン：前回動かした位置から一定距離未満なら動かさない
        new_pos = (int(round(sx)), int(round(sy)))
        if self.last_moved is not None and calc_distance(new_pos, self.last_moved) < DEAD_ZONE_PX:
            return
        pyautogui.moveTo(new_pos[0], new_pos[1])
        self.last_moved = new_pos


class ScrollController:
    """スクロール保持モード：開始時の鼻先の高さを基準に、顔の上下でスクロールする

    顔を上に向ける（鼻先が映像の上へ動く）と上へ、下に向けると下へスクロールする。
    基準からの距離が大きいほど速くスクロールする。
    """

    def __init__(self):
        self.active = False
        self.origin_y = None     # 開始時の鼻先のy座標（正規化座標）
        self.smoothed_y = None   # 平滑化した鼻先のy座標
        self.last_time = None
        self.accum = 0.0         # 端数のスクロール量（ホイール量）を次フレームへ持ち越す
        self.direction = 0       # 1=上, -1=下, 0=停止（表示用）

    def start(self, nose_y, now):
        """スクロール保持モードを開始する"""
        self.active = True
        self.origin_y = nose_y
        self.smoothed_y = nose_y
        self.last_time = now
        self.accum = 0.0
        self.direction = 0

    def stop(self):
        """スクロール保持モードを終了する"""
        self.active = False
        self.direction = 0

    def update(self, nose_y, now):
        """鼻先の高さに応じてスクロールする"""
        if not self.active:
            return
        dt = now - self.last_time
        self.last_time = now
        self.smoothed_y += SMOOTHING_ALPHA * (nose_y - self.smoothed_y)
        dy = self.smoothed_y - self.origin_y
        if abs(dy) < SCROLL_DEAD_ZONE:
            self.direction = 0
            self.accum = 0.0
            return
        notches_per_sec = min((abs(dy) - SCROLL_DEAD_ZONE) * SCROLL_SPEED_GAIN,
                              SCROLL_MAX_NOTCHES_PER_SEC)
        # 鼻先が上へ動く（yが小さくなる）と上スクロール（正の値）
        self.direction = 1 if dy < 0 else -1
        self.accum += self.direction * notches_per_sec * WHEEL_DELTA * dt
        amount = int(self.accum)
        if amount != 0:
            pyautogui.scroll(amount)
            self.accum -= amount

    def label(self, arrows):
        """状態表示用の文字列。arrows=True で矢印記号（オーバーレイ用）、False で英字（OpenCV用）"""
        if self.direction > 0:
            return "SCROLL ▲" if arrows else "SCROLL UP"
        if self.direction < 0:
            return "SCROLL ▼" if arrows else "SCROLL DOWN"
        return "SCROLL"


class GlobalHotkeys:
    """ウィンドウのフォーカスに関係なくホットキーを検出する（Windowsのみ）

    GetAsyncKeyState でキーの押下状態を毎フレーム確認し、
    「押されていない → 押された」に変わった瞬間だけを1回の入力として扱う。
    キー入力を横取りしないため、他のアプリにも同じキーは届く。
    """

    def __init__(self):
        self.enabled = sys.platform.startswith("win")
        self.was_pressed = {vk: False for vk, _ in HOTKEY_ACTIONS}
        if self.enabled:
            self.user32 = ctypes.windll.user32
        else:
            print("注意: グローバルホットキーは Windows でのみ使用できます。")

    def _is_down(self, vk):
        # 戻り値の最上位ビットが立っていれば、そのキーは現在押されている
        return bool(self.user32.GetAsyncKeyState(vk) & 0x8000)

    def poll(self):
        """押された瞬間のホットキーの操作名（HOTKEY_ACTIONS 参照）または None を返す"""
        if not self.enabled:
            return None
        modifiers_down = all(self._is_down(vk) for vk in HOTKEY_MODIFIERS)
        result = None
        for vk, name in HOTKEY_ACTIONS:
            pressed = modifiers_down and self._is_down(vk)
            if pressed and not self.was_pressed[vk] and result is None:
                result = name
            self.was_pressed[vk] = pressed
        return result


class StatusOverlay:
    """画面上部中央に、常に最前面・半透明・クリック透過の状態表示を出す（tkinter使用）

    メインループから毎フレーム update() を呼び、tkinter のイベント処理もそこで行う。
    マウス操作を邪魔しないよう、Windows ではクリックを下のウィンドウへ透過させる。
    """

    # Windows API の定数（拡張ウィンドウスタイル）
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020   # クリックを透過する
    WS_EX_TOOLWINDOW = 0x00000080    # タスクバー・Alt+Tab に出さない
    WS_EX_NOACTIVATE = 0x08000000    # クリックされてもフォーカスを奪わない

    def __init__(self, screen_w):
        self.screen_w = screen_w
        self.root = None
        self.last_text = None
        if not SHOW_STATUS_OVERLAY:
            return
        if tk is None:
            print("注意: tkinter が使えないため、画面上部の状態表示は行いません。")
            return
        try:
            self.root = tk.Tk()
            self.root.overrideredirect(True)          # 枠・タイトルバーなし
            self.root.attributes("-topmost", True)    # 常に最前面
            self.root.attributes("-alpha", OVERLAY_ALPHA)
            self.root.configure(bg=OVERLAY_BG)
            self.label = tk.Label(self.root, text="", font=OVERLAY_FONT,
                                  bg=OVERLAY_BG, fg=OVERLAY_COLORS["paused"], padx=8, pady=1)
            self.label.pack()
            self.root.update_idletasks()
            self._make_click_through()
        except tk.TclError as e:
            print("注意: 状態表示を作成できませんでした（{}）。表示なしで続行します。".format(e))
            self.root = None

    def _make_click_through(self):
        """Windows でクリック透過・タスクバー非表示にする"""
        if not sys.platform.startswith("win"):
            return
        user32 = ctypes.windll.user32
        # overrideredirect したウィンドウの実体（トップレベル）は winfo_id の親
        hwnd = user32.GetParent(self.root.winfo_id())
        style = user32.GetWindowLongW(hwnd, self.GWL_EXSTYLE)
        style |= (self.WS_EX_LAYERED | self.WS_EX_TRANSPARENT
                  | self.WS_EX_TOOLWINDOW | self.WS_EX_NOACTIVATE)
        user32.SetWindowLongW(hwnd, self.GWL_EXSTYLE, style)

    def update(self, state, text):
        """表示内容を更新し、tkinter のイベントを処理する

        state: "active" / "paused" / "no_face"（文字色の切り替え用）
        """
        if self.root is None:
            return
        try:
            if text != self.last_text:
                self.label.configure(text=text, fg=OVERLAY_COLORS[state])
                self.root.update_idletasks()
                # 文字幅が変わるたびに、画面中央へ配置し直す
                w = self.root.winfo_reqwidth()
                x = int((self.screen_w - w) / 2)
                self.root.geometry("+{}+{}".format(x, OVERLAY_TOP_PX))
                self.last_text = text
            self.root.update()
        except tk.TclError as e:
            print("注意: 状態表示の更新に失敗したため、表示を停止します（{}）。".format(e))
            self.root = None

    def close(self):
        """状態表示を閉じる"""
        if self.root is not None:
            try:
                self.root.destroy()
            except tk.TclError as e:
                print("注意: 状態表示を閉じる際にエラーが発生しました（{}）。".format(e))
            self.root = None


def create_landmarker():
    """Face Landmarker を生成する（モデルファイルがなければ例外）"""
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            "モデルファイルが見つかりません: {}\n"
            "以下のURLから face_landmarker.task を入手し、上記の場所に配置してください。\n"
            "  {}".format(MODEL_PATH, MODEL_URL)
        )
    options = vision.FaceLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL_PATH)),
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1,
    )
    return vision.FaceLandmarker.create_from_options(options)


def open_camera():
    """カメラを開く（開けなければ例外）"""
    # Windows では DirectShow を指定すると起動が速く安定しやすい
    backend = cv2.CAP_DSHOW if sys.platform.startswith("win") else cv2.CAP_ANY
    cap = cv2.VideoCapture(CAMERA_INDEX, backend)
    if not cap.isOpened():
        cap.release()
        raise RuntimeError(
            "カメラ（番号 {}）を開けませんでした。\n"
            "カメラの接続、他のアプリでの使用中、Windowsのカメラのプライバシー設定を"
            "確認してください。".format(CAMERA_INDEX)
        )
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
    return cap


def draw_landmarks(frame, landmarks):
    """鼻先・目のランドマークを映像に描画する"""
    h, w = frame.shape[:2]
    if SHOW_ALL_LANDMARKS:
        for lm in landmarks:
            cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 1, (180, 180, 180), -1)
    for idx in LEFT_EYE_POINTS + RIGHT_EYE_POINTS:
        lm = landmarks[idx]
        cv2.circle(frame, (int(lm.x * w), int(lm.y * h)), 2, (0, 255, 0), -1)
    nose = landmarks[NOSE_TIP]
    cv2.circle(frame, (int(nose.x * w), int(nose.y * h)), 5, (0, 0, 255), -1)


def draw_status(frame, paused, ear_left, ear_right, face_found, click_msg):
    """状態・EAR値・操作説明を映像に描画する（OpenCVの制約で英字表示）"""
    if paused:
        status, color = "PAUSED", (0, 165, 255)
    elif not face_found:
        status, color = "NO FACE", (0, 0, 255)
    else:
        status, color = "ACTIVE", (0, 200, 0)
    cv2.putText(frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
    if paused:
        cv2.putText(frame, "Close both eyes {:.0f}s to activate".format(ACTIVATE_HOLD_SEC),
                    (140, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    if ear_left is not None:
        for i, (label, ear) in enumerate((("L-EAR", ear_left), ("R-EAR", ear_right))):
            ear_color = (0, 0, 255) if ear < EAR_CLOSED_THRESHOLD else (255, 255, 255)
            cv2.putText(frame, "{}: {:.3f}".format(label, ear), (10, 60 + i * 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, ear_color, 2)

    if click_msg:
        cv2.putText(frame, click_msg, (10, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

    h = frame.shape[0]
    cv2.putText(frame, "Ctrl+Alt+P:pause  Ctrl+Alt+Q:quit (global)", (10, h - 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    cv2.putText(frame, "p:pause  c:center  q/ESC:quit", (10, h - 12),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


def run():
    """メインループ"""
    screen_w, screen_h = pyautogui.size()
    print("画面サイズ: {} x {}".format(screen_w, screen_h))

    landmarker = create_landmarker()
    cap = open_camera()
    cursor = CursorController(screen_w, screen_h)
    wink = WinkDetector()
    scroll = ScrollController()
    hotkeys = GlobalHotkeys()
    overlay = StatusOverlay(screen_w)

    # ホットキーが使えない環境では、ウィンドウがないと終了できないため常に表示する
    show_window = SHOW_WINDOW_ON_START or not hotkeys.enabled
    center_requested = False   # 中心の再設定要求（顔が検出されたフレームで反映する）
    paused = START_PAUSED
    both_closed_start = None   # 両目を閉じ始めた時刻（有効／無効の切り替え判定用）
    # 切り替え直後は、いったん目を開けるまで次の計測を始めない
    # （閉じ続けたまま 有効→無効→有効… と連続で切り替わるのを防ぐ）
    wait_eyes_open = False
    click_msg = ""
    click_msg_until = 0.0
    start_time = time.monotonic()
    last_timestamp_ms = -1

    if paused:
        print("起動しました（無効状態）。両目を{:.0f}秒閉じると有効になります。".format(ACTIVATE_HOLD_SEC))
        print("有効になったときの顔の位置がカーソルの中心になります。")
    else:
        print("起動しました。正面を向いた位置が中心になります。")
    print("有効中に両目を{:.0f}秒閉じると無効に戻ります。".format(DEACTIVATE_HOLD_SEC))
    if hotkeys.enabled:
        print("操作: Ctrl+Alt+P=一時停止/再開, Ctrl+Alt+C=中心の再設定, "
              "Ctrl+Alt+W=確認ウィンドウ表示/非表示, Ctrl+Alt+Q=終了")
    print("確認ウィンドウ選択時: p=一時停止/再開, c=中心の再設定, q/ESC=終了")
    print("緊急停止: 実際のマウスを画面の四隅へ動かしてください。")

    try:
        while True:
            # グローバルホットキーは、マウス操作より前に確認してすぐ反映させる
            hotkey = hotkeys.poll()
            if hotkey == "quit":
                print("Ctrl+Alt+Q により終了します。")
                break
            elif hotkey == "pause":
                paused = not paused
                wink.reset()
                both_closed_start = None
                print("一時停止しました。" if paused else "再開しました。")
            elif hotkey == "center":
                center_requested = True
            elif hotkey == "window":
                show_window = not show_window
                if not show_window:
                    cv2.destroyWindow(WINDOW_NAME)
                    cv2.waitKey(1)  # ウィンドウを閉じる処理をOpenCVに反映させる
                print("確認ウィンドウを表示しました。" if show_window else "確認ウィンドウを閉じました。")

            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("カメラから映像を取得できませんでした。接続を確認してください。")

            now = time.monotonic()
            # VIDEOモードではタイムスタンプが単調増加である必要がある
            timestamp_ms = max(int((now - start_time) * 1000), last_timestamp_ms + 1)
            last_timestamp_ms = timestamp_ms

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            result = landmarker.detect_for_video(mp_image, timestamp_ms)

            face_found = bool(result.face_landmarks)
            ear_left = ear_right = None

            if face_found:
                landmarks = result.face_landmarks[0]
                h, w = frame.shape[:2]
                ear_left = calc_ear(landmarks, LEFT_EYE_POINTS, w, h)
                ear_right = calc_ear(landmarks, RIGHT_EYE_POINTS, w, h)
                nose = landmarks[NOSE_TIP]

                if center_requested:
                    cursor.calibrate(nose.x, nose.y)
                    center_requested = False
                    print("現在の顔の位置を中心に再設定しました。")

                # 両目を一定時間閉じ続けたら有効／無効を切り替える
                # （無効→有効は ACTIVATE_HOLD_SEC、有効→無効は DEACTIVATE_HOLD_SEC）
                if ear_left < EAR_CLOSED_THRESHOLD and ear_right < EAR_CLOSED_THRESHOLD:
                    if wait_eyes_open:
                        pass
                    elif both_closed_start is None:
                        both_closed_start = now
                    else:
                        required = ACTIVATE_HOLD_SEC if paused else DEACTIVATE_HOLD_SEC
                        if now - both_closed_start >= required:
                            paused = not paused
                            both_closed_start = None
                            wait_eyes_open = True
                            wink.reset()
                            if paused:
                                click_msg, click_msg_until = "DEACTIVATED", now + 1.5
                                print("両目を閉じる操作により無効にしました。")
                            else:
                                # 目を開ける動作で誤クリックしないようクールダウンを入れる
                                wink.start_cooldown(now)
                                click_msg, click_msg_until = "ACTIVATED", now + 1.5
                                print("両目を閉じる操作により有効になりました。")
                else:
                    both_closed_start = None
                    wait_eyes_open = False

                if not paused:
                    action = wink.update(ear_left, ear_right, now)
                    # クリックは目を開けたフレームで確定するため、
                    # カーソルを動かす前にクリックして位置ズレを防ぐ
                    if action and scroll.active:
                        # スクロール保持中は、どのウインクでも解除のみ行う（クリックはしない）
                        scroll.stop()
                        click_msg, click_msg_until = "SCROLL OFF", now + 0.8
                        print("スクロール保持モードを終了しました。")
                        action = None
                    elif action == "scroll":
                        scroll.start(nose.y, now)
                        click_msg, click_msg_until = "SCROLL ON", now + 0.8
                        print("スクロール保持モードを開始しました（顔を上下に向けてスクロール、ウインクで解除）。")
                        action = None
                    elif action == "left":
                        pyautogui.click(button="left")
                        click_msg, click_msg_until = "LEFT CLICK", now + 0.8
                    elif action == "double":
                        pyautogui.doubleClick(button="left")
                        click_msg, click_msg_until = "DOUBLE CLICK", now + 0.8
                    elif action == "right":
                        pyautogui.click(button="right")
                        click_msg, click_msg_until = "RIGHT CLICK", now + 0.8
                    if action and not show_window:
                        # ウィンドウ非表示時はコンソールで操作結果を確認できるようにする
                        print("クリック: {}".format(click_msg))
                    if scroll.active:
                        # スクロール保持中はカーソルを止め、顔の上下でスクロールする
                        scroll.update(nose.y, now)
                        cursor.update(nose.x, nose.y, freeze=True)
                    else:
                        freeze = FREEZE_CURSOR_WHILE_WINK and wink.is_any_eye_closing()
                        cursor.update(nose.x, nose.y, freeze=freeze)

                if show_window:
                    draw_landmarks(frame, landmarks)
            else:
                # 顔を見失ったらウインク判定・切り替えの計測を途中から再開しないようリセット
                wink.reset()
                both_closed_start = None

            # 無効になったらスクロール保持も終了する（ホットキー・キー・両目の操作のいずれでも）
            if paused and scroll.active:
                scroll.stop()
                print("無効になったため、スクロール保持モードを終了しました。")

            msg = click_msg if now < click_msg_until else ""
            # ウインク中は経過秒数を表示し、ダブルクリック／スクロール開始までの目安にする
            for side, prefix in (("left", "L"), ("right", "R")):
                hold = wink.get_hold_time(side, now)
                if not msg and hold > 0 and not wink.fired[side]:
                    msg = "{}-HOLD {:.1f}s / {:.1f}s".format(prefix, hold, wink.long_hold_sec(side))
            # 両目を閉じている間は、切り替えまでの経過秒数を表示する
            if not msg and both_closed_start is not None:
                closed_sec = now - both_closed_start
                if closed_sec >= EYES_CLOSED_MSG_DELAY_SEC:
                    if paused:
                        msg = "ACTIVATING {:.1f}s / {:.1f}s".format(closed_sec, ACTIVATE_HOLD_SEC)
                    else:
                        msg = "DEACTIVATING {:.1f}s / {:.1f}s".format(closed_sec, DEACTIVATE_HOLD_SEC)

            # 画面上部中央の状態表示（ウィンドウの表示有無に関係なく常に更新）
            if paused:
                state, text = "paused", "顔マウス：無効（両目{:.0f}秒で有効）".format(ACTIVATE_HOLD_SEC)
            elif not face_found:
                state, text = "no_face", "顔マウス：顔が見つかりません"
            else:
                state, text = "active", "顔マウス：有効"
            if msg:
                text += "　" + msg
            elif scroll.active:
                text += "　" + scroll.label(arrows=True)
            overlay.update(state, text)

            # ウィンドウ非表示時は描画とキー入力処理を省略する（負荷軽減）
            if not show_window:
                continue

            # 本人が見やすいよう、表示は鏡像にする（判定は反転前の映像で実施済み）
            display = cv2.flip(frame, 1)
            if not msg and scroll.active:
                msg = scroll.label(arrows=False)
            draw_status(display, paused, ear_left, ear_right, face_found, msg)
            cv2.imshow(WINDOW_NAME, display)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):  # 27 = ESC
                print("終了します。")
                break
            elif key == ord("p"):
                paused = not paused
                wink.reset()
                both_closed_start = None
                print("一時停止しました。" if paused else "再開しました。")
            elif key == ord("c") and face_found:
                cursor.calibrate(nose.x, nose.y)
                print("現在の顔の位置を中心に再設定しました。")

            # ウィンドウの×ボタンで閉じられた場合、ホットキーがあれば非表示にするだけで動作は続ける。
            # ホットキーが使えない環境では操作手段がなくなるため終了する
            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                if hotkeys.enabled:
                    show_window = False
                    print("確認ウィンドウを閉じました（動作は継続中。Ctrl+Alt+W で再表示、Ctrl+Alt+Q で終了）。")
                else:
                    print("ウィンドウが閉じられたため終了します。")
                    break
    finally:
        cap.release()
        landmarker.close()
        overlay.close()
        cv2.destroyAllWindows()


def main():
    try:
        run()
    except pyautogui.FailSafeException:
        print("FAILSAFE が発動しました（マウスが画面の四隅に移動）。安全のため終了します。")
        sys.exit(1)
    except FileNotFoundError as e:
        print("エラー: {}".format(e))
        sys.exit(1)
    except RuntimeError as e:
        print("エラー: {}".format(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print("Ctrl+C により終了します。")


if __name__ == "__main__":
    main()
