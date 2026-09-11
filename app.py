"""売上データダッシュボード用のローカルサーバー。

同じ列構成(日付,商品名,カテゴリ,地域,数量,単価,売上金額)のCSVを
このディレクトリから自動検出し、ブラウザ側で選択・集計できるようにする。
"""

import csv
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
EXPECTED_HEADER = ["日付", "商品名", "カテゴリ", "地域", "数量", "単価", "売上金額"]

app = Flask(__name__, static_folder=None)


def _read_csv(path: Path):
    """ヘッダーが一致するCSVのみ読み込む。一致しなければNoneを返す。"""
    try:
        with path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header != EXPECTED_HEADER:
                return None
            rows = []
            for r in reader:
                if len(r) != 7:
                    continue
                date, product, category, region, qty, unit, total = r
                rows.append(
                    {
                        "d": date,
                        "p": product,
                        "c": category,
                        "r": region,
                        "q": int(qty),
                        "u": int(unit),
                        "t": int(total),
                    }
                )
            return rows
    except (OSError, UnicodeDecodeError, ValueError):
        return None


def discover_csv_files():
    """同じ形式のCSVをこのフォルダ直下から探す(サブフォルダは対象外)。"""
    found = []
    for path in sorted(BASE_DIR.glob("*.csv")):
        rows = _read_csv(path)
        if rows is None:
            continue
        dates = [r["d"] for r in rows]
        found.append(
            {
                "filename": path.name,
                "rows": len(rows),
                "minDate": min(dates) if dates else None,
                "maxDate": max(dates) if dates else None,
            }
        )
    return found


@app.get("/api/files")
def api_files():
    return jsonify(discover_csv_files())


@app.get("/api/data")
def api_data():
    valid_names = {f["filename"] for f in discover_csv_files()}
    requested = [n for n in request.args.get("files", "").split(",") if n]
    unknown = [n for n in requested if n not in valid_names]
    if unknown:
        return jsonify({"error": f"未対応または見つからないファイル: {', '.join(unknown)}"}), 400

    combined = []
    for name in requested:
        combined.extend(_read_csv(BASE_DIR / name) or [])
    return jsonify(combined)


@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.get("/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


if __name__ == "__main__":
    app.run(port=5050, debug=True)
