"""测试 1：HTTP 接口能不能正常工作，以及边界情况会不会被拦住。"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    """健康检查接口应该返回 ok。"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_predict_normal():
    """正常输入应该返回一个正数的价格。"""
    response = client.post(
        "/api/predict",
        json={"year": 2020, "mileage_km": 50000, "engine_l": 2.0},
    )
    assert response.status_code == 200
    price = response.json()["predicted_price"]
    assert price > 0


def test_predict_more_mileage_is_cheaper():
    """里程多的车，价格应该更低（边界：两端各一辆）。"""
    low = client.post(
        "/api/predict",
        json={"year": 2020, "mileage_km": 10000, "engine_l": 2.0},
    ).json()["predicted_price"]

    high = client.post(
        "/api/predict",
        json={"year": 2020, "mileage_km": 200000, "engine_l": 2.0},
    ).json()["predicted_price"]

    assert low > high


def test_predict_rejects_negative_mileage():
    """里程是负数 -> 422。"""
    response = client.post(
        "/api/predict",
        json={"year": 2020, "mileage_km": -1, "engine_l": 2.0},
    )
    assert response.status_code == 422


def test_predict_rejects_year_too_old():
    """年份太早（1890）-> 422。"""
    response = client.post(
        "/api/predict",
        json={"year": 1890, "mileage_km": 50000, "engine_l": 2.0},
    )
    assert response.status_code == 422


def test_predict_rejects_year_below_training_range():
    """1990 年超出训练数据范围（2005-2024）-> 422。

    为什么必须挡住：模型对 2005 年以前是外推，二次项会把价格算高，
    实际会出现「1990 年比 2010 年贵」这种不可信结果。
    """
    response = client.post(
        "/api/predict",
        json={"year": 1990, "mileage_km": 100000, "engine_l": 2.0},
    )
    assert response.status_code == 422


def test_predict_rejects_year_above_training_range():
    """2025 年也超出训练范围（数据只到 2024）-> 422。"""
    response = client.post(
        "/api/predict",
        json={"year": 2025, "mileage_km": 100000, "engine_l": 2.0},
    )
    assert response.status_code == 422


def test_predict_rejects_wrong_type():
    """年份写成文字 -> 422。"""
    response = client.post(
        "/api/predict",
        json={"year": "很老", "mileage_km": 50000, "engine_l": 2.0},
    )
    assert response.status_code == 422


def test_predict_rejects_missing_field():
    """少传排量字段 -> 422。"""
    response = client.post(
        "/api/predict",
        json={"year": 2020, "mileage_km": 50000},
    )
    assert response.status_code == 422
