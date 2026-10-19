"""训练三个模型，把结果记录到 MLflow，最后挑误差最小的上线。

实验 1：linear      —— 线性回归，直接用原始三列（基线）
实验 2：linear_age2 —— 线性回归 + 特征工程（把年份换成车龄，再加车龄平方）
实验 3：forest      —— 随机森林（很多棵决策树投票）

运行方法（在项目根目录）：
    python -m ml.train

运行完：
    models/model.pkl     = 误差最小的那个模型
    models/metrics.json  = 每个模型的指标
    mlruns/              = MLflow 的实验记录
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path

import joblib
import yaml
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

# MLflow 3 默认不允许把记录存进本地文件夹，这里显式放开，
# 这样实验记录就存在项目里的 mlruns/ 目录，用 mlflow ui 就能看。
os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

import mlflow

from ml.data_pipeline import (
    load_rows,
    make_xy,
    make_xy_with_features,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "cars_v2.csv"
PARAMS_PATH = BASE_DIR / "ml" / "configs" / "params.yaml"
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)


def get_git_commit():
    """取当前代码的 git 提交号，记进 MLflow，方便以后对账。"""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            text=True,
            cwd=BASE_DIR,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "no-git"


def train_one(
    name, model, feature_set, X, y, data_hash, commit, params, model_params=None
):
    """训练一个模型、算两个指标、记录到 MLflow，返回结果。

    model_params 是这个模型自己的超参数（例如随机森林的 n_estimators / max_depth）。
    线性回归没有超参数，传空字典即可，这样 MLflow 里就不会出现「不属于它的参数」。
    """
    # 同一个 random_state 保证三个实验用的是同一份训练集和测试集
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=params["test_size"], random_state=params["random_state"]
    )

    with mlflow.start_run(run_name=name):
        model.fit(X_train, y_train)
        pred = model.predict(X_test)

        mae = mean_absolute_error(y_test, pred)
        r2 = r2_score(y_test, pred)

        # 记参数：以后能回答“这个结果是怎么跑出来的”
        mlflow.log_param("model", name)
        mlflow.log_param("feature_set", feature_set)
        mlflow.log_param("train_rows", len(X_train))
        mlflow.log_param("test_rows", len(X_test))
        mlflow.log_param("dataset_hash", data_hash)
        mlflow.log_param("git_commit", commit)
        mlflow.log_param("test_size", params["test_size"])
        mlflow.log_param("random_state", params["random_state"])

        # 记这个模型自己的超参数：森林的 n_estimators / max_depth 就在这里进 MLflow
        if model_params:
            mlflow.log_params(model_params)

        # 记指标：用来比较模型好坏
        mlflow.log_metric("mae", mae)
        mlflow.log_metric("r2", r2)

        # 记模型文件
        model_path = MODELS_DIR / (name + ".pkl")
        joblib.dump(model, model_path)
        mlflow.log_artifact(str(model_path))

        print(f"{name:<12} MAE = {mae:6.0f}   R2 = {r2:.3f}")
        return {
            "mae": mae,
            "r2": r2,
            "feature_set": feature_set,
            "model": model,
            # 记录真实切分后的行数：136 行按 8:2 切，sklearn 会得到 108 / 28
            "train_rows": len(X_train),
            "test_rows": len(X_test),
        }


def main():
    params = yaml.safe_load(PARAMS_PATH.read_text(encoding="utf-8"))

    rows = load_rows(DATA_PATH)
    print(f"读入数据：{len(rows)} 行（{DATA_PATH.name}）")

    X_raw, y_raw = make_xy(rows)
    X_age2, y_age2 = make_xy_with_features(rows)

    data_hash = hashlib.md5(DATA_PATH.read_bytes()).hexdigest()[:8]
    commit = get_git_commit()
    print(f"数据指纹：{data_hash}    代码版本：{commit}")
    print()

    # MLflow 的记录存在项目里的 mlruns 文件夹
    mlflow.set_tracking_uri((BASE_DIR / "mlruns").as_uri())
    mlflow.set_experiment("car-price")

    experiments = [
        ("linear", LinearRegression(), "raw", X_raw, y_raw, {}),
        ("linear_age2", LinearRegression(), "age2", X_age2, y_age2, {}),
        (
            "forest",
            RandomForestRegressor(
                n_estimators=params["forest"]["n_estimators"],
                max_depth=params["forest"]["max_depth"],
                random_state=params["random_state"],
            ),
            "raw",
            X_raw,
            y_raw,
            {
                "n_estimators": params["forest"]["n_estimators"],
                "max_depth": params["forest"]["max_depth"],
            },
        ),
    ]

    results = {}
    for name, model, feature_set, X, y, model_params in experiments:
        result = train_one(
            name,
            model,
            feature_set,
            X,
            y,
            data_hash,
            commit,
            params,
            model_params,
        )
        results[name] = result

    # 谁的 MAE 小，就让谁上线
    best_name = min(results, key=lambda name: results[name]["mae"])
    best = results[best_name]
    joblib.dump(best["model"], MODELS_DIR / "model.pkl")

    info = {
        "best_model": best_name,
        "feature_set": best["feature_set"],
        "dataset": DATA_PATH.name,
        "dataset_hash": data_hash,
        "git_commit": commit,
        "train_rows": best["train_rows"],
        "test_rows": best["test_rows"],
        "results": {
            name: {
                "mae": round(r["mae"], 2),
                "r2": round(r["r2"], 4),
                "feature_set": r["feature_set"],
            }
            for name, r in results.items()
        },
    }
    (MODELS_DIR / "metrics.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    print()
    print(f"上线的模型：{best_name}（{best['feature_set']}）")
    print("指标写入 models/metrics.json")


if __name__ == "__main__":
    main()
