# -*- coding: utf-8 -*-
"""docs/CODEMAP.md を自動生成するスクリプト

scripts/ 配下の Python ファイルを ast で解析し、
ファイルごとに「役割1行（モジュールdocstringの1行目）＋主要シンボル（クラス・公開関数）」を出力する。
構造を変更したら（ファイル追加・移動・削除、公開関数の追加など）再実行すること。

使い方:
    uv run scripts/gen_codemap.py
"""

import ast
import datetime
import sys
from pathlib import Path

# ============================================================
# パラメータ
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent.parent
TARGET_DIRS = ["scripts"]                       # 解析対象のディレクトリ（ROOT_DIR からの相対）
OUTPUT_PATH = ROOT_DIR / "docs" / "CODEMAP.md"
STALE_AFTER_DAYS = 90                           # stale_after に設定する日数
MAX_METHODS = 5                                 # クラスごとに列挙するメソッドの最大数


def first_line(docstring):
    """docstring の1行目を返す（無ければ空文字）"""
    if not docstring:
        return ""
    return docstring.strip().splitlines()[0].strip()


def format_args(func_node):
    """関数の引数名をカンマ区切りで返す（self は除く）"""
    names = [a.arg for a in func_node.args.args if a.arg != "self"]
    return ", ".join(names)


def collect_symbols(tree):
    """モジュール直下のクラス・公開関数を (表示名, 説明) のリストで返す"""
    symbols = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            methods = [
                n.name for n in node.body
                if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
            ]
            label = "`{}`".format(node.name)
            if methods:
                shown = methods[:MAX_METHODS]
                suffix = ", …" if len(methods) > MAX_METHODS else ""
                label += "（{}{}）".format(", ".join(shown), suffix)
            symbols.append((label, first_line(ast.get_docstring(node))))
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            label = "`{}({})`".format(node.name, format_args(node))
            symbols.append((label, first_line(ast.get_docstring(node))))
    return symbols


def parse_file(path):
    """1ファイルを解析し、(役割, シンボル一覧) を返す"""
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        print("ファイルを読み込めませんでした: {} ({})".format(path, e))
        raise
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        print("構文エラーのため解析できませんでした: {} ({})".format(path, e))
        raise
    return first_line(ast.get_docstring(tree)), collect_symbols(tree)


def build_markdown(entries, now):
    """CODEMAP.md の本文を組み立てる"""
    stale = (now + datetime.timedelta(days=STALE_AFTER_DAYS)).date().isoformat()
    lines = [
        "---",
        "type: Code Map",
        "title: コード構造マップ",
        "description: scripts/ 配下の各ファイルの役割と主要シンボル（gen_codemap.py による自動生成）",
        "tags: [codemap, generated]",
        "generated:",
        "  by: script:scripts/gen_codemap.py",
        "  at: {}".format(now.strftime("%Y-%m-%dT%H:%M:%SZ")),
        "stale_after: {}".format(stale),
        "status: stable",
        "---",
        "",
        "# コード構造マップ",
        "",
        "> このファイルは [scripts/gen_codemap.py](../scripts/gen_codemap.py) で自動生成しています。"
        "手で編集せず、`uv run scripts/gen_codemap.py` を再実行してください。",
        "",
    ]
    for rel_path, role, symbols in entries:
        lines.append("## [{0}](../{0})".format(rel_path))
        lines.append("")
        lines.append(role or "（モジュールdocstringなし）")
        lines.append("")
        for label, desc in symbols:
            lines.append("- {}{}".format(label, " … " + desc if desc else ""))
        if symbols:
            lines.append("")
    return "\n".join(lines)


def main():
    entries = []
    for target in TARGET_DIRS:
        for path in sorted((ROOT_DIR / target).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            role, symbols = parse_file(path)
            rel_path = path.relative_to(ROOT_DIR).as_posix()
            entries.append((rel_path, role, symbols))
            print("解析: {}（シンボル {} 件）".format(rel_path, len(symbols)))

    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(build_markdown(entries, now), encoding="utf-8")
    except OSError as e:
        print("CODEMAP.md を書き込めませんでした: {} ({})".format(OUTPUT_PATH, e))
        sys.exit(1)
    print("生成しました: {}".format(OUTPUT_PATH))


if __name__ == "__main__":
    main()
