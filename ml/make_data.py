"""生成练习用的二手车数据。

v1 = 原始数据（最后 4 行是故意放进去的错误数据）
v2 = 清洗后的数据（去掉 4 行错误，再补 20 行正常数据）

运行方法（在项目根目录）：
    python ml/make_data.py
"""

import csv
import random
from pathlib import Path

random.seed(7)

# 项目根目录（本文件在 ml/ 里面，所以往上退一层）
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)


def make_row():
    """按一个简单的市场规律造一条车价数据。"""
    year = random.randint(2005, 2024)
    mileage_km = random.randint(10000, 250000)
    engine_l = round(random.uniform(1.0, 4.0), 1)

    age = 2026 - year
    # 车越老越便宜（每老一年打九折），排量越大越贵，里程越多越便宜
    price = 26000 * (0.90**age) + 5000 * engine_l - 0.03 * mileage_km
    price = price + random.uniform(-1200, 1200)
    price = max(price, 1500)
    return [year, mileage_km, engine_l, round(price)]


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["year", "mileage_km", "engine_l", "price_eur"])
        writer.writerows(rows)


def main():
    good_rows = [make_row() for _ in range(116)]

    # v1：好数据 + 4 行明显错误的数据
    bad_rows = [
        [1890, 50000, 2.0, 20000],  # 年份不可能这么早
        [2018, -500, 2.0, 18000],  # 里程是负数
        [2019, 80000, 0.0, 15000],  # 排量是 0
        [2020, 60000, 2.0, 999999],  # 价格离谱
    ]
    write_csv(DATA_DIR / "cars_v1.csv", good_rows + bad_rows)

    # v2：去掉 4 行错误，再补 20 行正常数据
    extra_rows = [make_row() for _ in range(20)]
    write_csv(DATA_DIR / "cars_v2.csv", good_rows + extra_rows)

    print("data/cars_v1.csv =", len(good_rows + bad_rows), "行")
    print("data/cars_v2.csv =", len(good_rows + extra_rows), "行")


if __name__ == "__main__":
    main()
