"""读 CSV，把表格变成机器学习要用的 X（特征）和 y（答案）。"""

import csv

# 模型看这三列来猜价格
FEATURES = ["year", "mileage_km", "engine_l"]

# 现在是哪一年（用来算车龄）
THIS_YEAR = 2026


def load_rows(path):
    """把 CSV 文件读成一个列表，每个元素是一行的字典。"""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def make_xy(rows):
    """版本 A（最简单）：直接用原始三列。

    X 是二维列表：每一行是 [年份, 里程, 排量]
    y 是一维列表：每一行是这个车的真实价格
    """
    X = []
    y = []
    for row in rows:
        X.append([int(row["year"]), int(row["mileage_km"]), float(row["engine_l"])])
        y.append(float(row["price_eur"]))
    return X, y


def make_xy_with_features(rows):
    """版本 B（特征工程）：把年份换成“车龄”，再加一个“车龄的平方”。

    为什么要加车龄平方？因为车价不是直线下跌的：
    前几年掉得快，后面掉得慢。加一个平方项，直线就能弯起来。
    """
    X = []
    y = []
    for row in rows:
        age = THIS_YEAR - int(row["year"])
        X.append([age, int(row["mileage_km"]), float(row["engine_l"]), age * age])
        y.append(float(row["price_eur"]))
    return X, y


def make_one_row(year, mileage_km, engine_l, feature_set):
    """把网页上收到的三个数字，变成模型要的那种格式。"""
    if feature_set == "age2":
        age = THIS_YEAR - year
        return [[age, mileage_km, engine_l, age * age]]
    return [[year, mileage_km, engine_l]]
