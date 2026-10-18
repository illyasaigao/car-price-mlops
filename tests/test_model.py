"""测试 2：模型本身靠不靠谱（不经过网站，直接调用模型）。"""

import json
from pathlib import Path

import joblib

from ml.data_pipeline import make_one_row

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "model.pkl"
INFO_PATH = BASE_DIR / "models" / "metrics.json"

INFO = json.loads(INFO_PATH.read_text(encoding="utf-8"))


def predict(year, mileage_km, engine_l):
    """和网站用同一套方式调用模型，避免测试和线上不一致。"""
    model = joblib.load(MODEL_PATH)
    features = make_one_row(year, mileage_km, engine_l, INFO["feature_set"])
    return model.predict(features)[0]


def test_model_file_exists():
    """训练完必须留下模型文件。"""
    assert MODEL_PATH.exists()


def test_three_experiments_recorded():
    """MLflow 里那三个实验的结果都要写进 metrics.json。"""
    assert "linear" in INFO["results"]
    assert "linear_age2" in INFO["results"]
    assert "forest" in INFO["results"]


def test_best_model_is_the_lowest_mae():
    """上线的一定是误差最小的那个模型。"""
    results = INFO["results"]
    lowest = min(results, key=lambda name: results[name]["mae"])
    assert INFO["best_model"] == lowest


def test_model_predicts_positive_price():
    """一辆正常的车，价格应该是正的。"""
    assert predict(2020, 50000, 2.0) > 0


def test_model_gives_lower_price_for_older_car():
    """同里程同排量，越老越便宜。"""
    assert predict(2023, 60000, 2.0) > predict(2008, 60000, 2.0)


def test_model_gives_lower_price_for_more_mileage():
    """同款车，里程越多越便宜。"""
    assert predict(2020, 20000, 2.0) > predict(2020, 220000, 2.0)
