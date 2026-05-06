from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

def load_data(category: str) -> dict:
    path = os.path.join(DATA_DIR, f"{category}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def find_closest_size(target_inner_mm: float, brand_data: dict) -> dict:
    sizes = brand_data["sizes"]
    best_size = None
    best_diff = float("inf")
    best_entry = None

    for size_label, entry in sizes.items():
        diff = abs(entry["inner_length_mm"] - target_inner_mm)
        if diff < best_diff:
            best_diff = diff
            best_size = size_label
            best_entry = entry

    return {
        "size_label": best_size,
        "inner_length_mm": best_entry["inner_length_mm"],
        "diff_mm": round(target_inner_mm - best_entry["inner_length_mm"], 1),
    }


@app.route("/api/brands", methods=["GET"])
def get_brands():
    """사용 가능한 브랜드 목록 반환"""
    category = request.args.get("category", "shoes")
    try:
        data = load_data(category)
        brands = [
            {
                "id": key,
                "display": val["display"],
                "sizes": sorted(val["sizes"].keys(), key=lambda x: int(x)),
            }
            for key, val in data["brands"].items()
        ]
        return jsonify({"brands": brands})
    except FileNotFoundError:
        return jsonify({"error": f"Category '{category}' not found"}), 404


@app.route("/api/convert", methods=["POST"])
def convert_size():
    """
    입력 브랜드+사이즈 → 실측 내부 길이 추출 → 기준 브랜드 nearest-match 변환
    Request body:
        {
            "category": "shoes",
            "input_brand": "Converse",
            "input_size": "270",
            "target_brand": "Nike"
        }
    """
    body = request.get_json()
    category    = body.get("category", "shoes")
    input_brand = body.get("input_brand")
    input_size  = str(body.get("input_size"))
    target_brand = body.get("target_brand")

    if not all([input_brand, input_size, target_brand]):
        return jsonify({"error": "input_brand, input_size, target_brand 모두 필요합니다."}), 400

    try:
        data = load_data(category)
    except FileNotFoundError:
        return jsonify({"error": f"Category '{category}' not found"}), 404

    brands = data["brands"]

    if input_brand not in brands:
        return jsonify({"error": f"브랜드 '{input_brand}'를 찾을 수 없습니다."}), 404
    if target_brand not in brands:
        return jsonify({"error": f"브랜드 '{target_brand}'를 찾을 수 없습니다."}), 404

    input_brand_data = brands[input_brand]
    if input_size not in input_brand_data["sizes"]:
        return jsonify({"error": f"'{input_brand}'에서 사이즈 '{input_size}'를 찾을 수 없습니다."}), 404

    # 1. 입력 브랜드의 실측 내부 길이 추출
    input_entry = input_brand_data["sizes"][input_size]
    inner_length = input_entry["inner_length_mm"]

    # 2. 기준 브랜드에서 가장 가까운 사이즈 찾기
    target_brand_data = brands[target_brand]
    matched = find_closest_size(inner_length, target_brand_data)

    # 3. 동일 브랜드 처리
    is_same_brand = (input_brand == target_brand)

    return jsonify({
        "input_brand":   input_brand,
        "input_size":    input_size,
        "target_brand":  target_brand,
        "recommended_size": matched["size_label"] if not is_same_brand else input_size,
        "is_same_brand": is_same_brand,
        "details": {
            "input_inner_length_mm": inner_length,
            "target_inner_length_mm": matched["inner_length_mm"],
            "length_diff_mm": matched["diff_mm"],
        }
    })


@app.route("/api/brand-info", methods=["GET"])
def brand_info():
    """특정 브랜드의 모든 사이즈별 실측 데이터 반환"""
    category = request.args.get("category", "shoes")
    brand    = request.args.get("brand")
    if not brand:
        return jsonify({"error": "brand 파라미터가 필요합니다."}), 400
    try:
        data = load_data(category)
    except FileNotFoundError:
        return jsonify({"error": f"Category '{category}' not found"}), 404

    if brand not in data["brands"]:
        return jsonify({"error": f"브랜드 '{brand}'를 찾을 수 없습니다."}), 404

    b = data["brands"][brand]
    return jsonify({
        "brand": brand,
        "display": b["display"],
        "region": b["region"],
        "notes": b["notes"],
        "width_tendency": b["width_tendency"],
        "fit_note": b["fit_note"],
        "sizes": b["sizes"],
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0",debug=True, port=5000)
