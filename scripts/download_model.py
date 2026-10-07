# -*- coding: utf-8 -*-
"""MediaPipe Face Landmarker のモデルファイルを取得するスクリプト

初回セットアップ時に一度だけ実行すればよい（約3.6MB）。
- 一時ファイルに保存してから置き換えるので、途中で失敗しても壊れたファイルは残らない
- 中身をハッシュ値で確かめる（途中で切れたファイル・別物のファイルを使わないため）
- 既にあるファイルも確かめ、壊れていれば取り直す

使い方:
    uv run scripts/download_model.py
"""

import hashlib
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

# ============================================================
# パラメータ
# ============================================================

MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/face_landmarker/"
             "face_landmarker/float16/1/face_landmarker.task")
# 上のURL（版 "1" 固定）で配布されているファイルの SHA-256 と大きさ
MODEL_SHA256 = "64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff"
MODEL_SIZE = 3758596
ROOT_DIR = Path(__file__).resolve().parent.parent
DEST_PATH = ROOT_DIR / "models" / "face_landmarker.task"


def sha256_of(path):
    """ファイルの SHA-256 を返す"""
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check_model(path=None):
    """モデルファイルが正しいか確かめる。問題なければ None、あれば理由を返す"""
    path = Path(path) if path is not None else DEST_PATH
    if not path.exists():
        return "ファイルがありません"
    size = path.stat().st_size
    if size != MODEL_SIZE:
        return "大きさが違います（{:,} bytes、正しくは {:,} bytes。途中で切れた可能性）".format(
            size, MODEL_SIZE)
    if sha256_of(path) != MODEL_SHA256:
        return "中身が配布物と一致しません（壊れているか、別のファイルです）"
    return None


def main():
    problem = check_model()
    if problem is None:
        print("既に存在します（確認済み）: {}（{:,} bytes）".format(DEST_PATH, MODEL_SIZE))
        return 0
    if DEST_PATH.exists():
        print("既存のモデルファイルを取り直します: {}".format(problem))

    DEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = DEST_PATH.with_name(DEST_PATH.name + ".download")
    print("ダウンロード中: {}".format(MODEL_URL))
    try:
        urllib.request.urlretrieve(MODEL_URL, str(tmp_path))
        problem = check_model(tmp_path)
        if problem is not None:
            raise ValueError("ダウンロードしたファイルが正しくありません: {}".format(problem))
        os.replace(str(tmp_path), str(DEST_PATH))
    except (urllib.error.URLError, OSError, ValueError) as e:
        print("ダウンロードに失敗しました: {}".format(e))
        print("社内プロキシ環境の場合は、ブラウザで上記URLを開いて {} に保存してから、"
              "もう一度このスクリプトを実行して確認してください。".format(DEST_PATH))
        try:
            tmp_path.unlink()
        except OSError as e2:
            # 一時ファイルが無い（ダウンロード前に失敗した）場合もここに来る
            print("（一時ファイルの削除はスキップしました: {}）".format(e2))
        return 1

    print("保存しました（確認済み）: {}（{:,} bytes）".format(DEST_PATH, MODEL_SIZE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
