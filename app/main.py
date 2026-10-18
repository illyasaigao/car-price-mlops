"""预测二手车价格的小网站。

启动（在项目根目录）：
    python -m uvicorn app.main:app --reload
然后打开 http://127.0.0.1:8000
"""

import json
from pathlib import Path

import joblib
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from ml.data_pipeline import make_one_row

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH = BASE_DIR / "models" / "model.pkl"
INFO_PATH = BASE_DIR / "models" / "metrics.json"

app = FastAPI(title="二手车价格预测")

# 程序启动时把模型和模型信息读进内存，之后每次预测直接用，不用重复读文件
model = joblib.load(MODEL_PATH)
info = json.loads(INFO_PATH.read_text(encoding="utf-8"))
feature_set = info["feature_set"]


class CarInput(BaseModel):
    """用户提交上来的三个数字，范围不对就直接报错 422。"""

    year: int = Field(ge=1990, le=2026)
    mileage_km: int = Field(ge=0, le=500000)
    engine_l: float = Field(ge=0.5, le=8.0)


@app.get("/")
def home():
    return FileResponse(BASE_DIR / "app" / "static" / "index.html")


@app.get("/health")
def health():
    """给运维和 CI 用的健康检查接口。"""
    return {"status": "ok"}


@app.post("/api/predict")
def predict(car: CarInput):
    """接收一辆车的信息，返回模型猜出来的价格。"""
    features = make_one_row(car.year, car.mileage_km, car.engine_l, feature_set)
    price = float(model.predict(features)[0])
    price = max(price, 0)  # 价格不会小于 0
    return {"predicted_price": round(price, 2)}


@app.get("/api/model-info")
def get_model_info():
    """返回模型的信息和指标，页面上会显示。"""
    return info
