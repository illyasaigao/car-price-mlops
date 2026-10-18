"""测试 3：数据处理和数据集版本（DVC 里那两个 CSV）。"""

from pathlib import Path

from ml.data_pipeline import load_rows, make_xy

BASE_DIR = Path(__file__).resolve().parent.parent


def test_v1_has_bad_rows():
    """v1 是原始数据，里面故意有 4 行错误数据。"""
    rows = load_rows(BASE_DIR / "data" / "cars_v1.csv")
    bad = [r for r in rows if int(r["year"]) < 1990 or int(r["mileage_km"]) < 0]
    assert len(bad) >= 2


def test_v2_is_clean():
    """v2 是清洗后的数据，不能有脏数据。"""
    rows = load_rows(BASE_DIR / "data" / "cars_v2.csv")

    for row in rows:
        assert 1990 <= int(row["year"]) <= 2026
        assert 0 <= int(row["mileage_km"]) <= 500000
        assert 0.5 <= float(row["engine_l"]) <= 8.0
        assert 0 < float(row["price_eur"]) < 200000


def test_v2_is_bigger_than_v1():
    """v2 去掉 4 行、补了 20 行，所以比 v1 多。"""
    v1 = load_rows(BASE_DIR / "data" / "cars_v1.csv")
    v2 = load_rows(BASE_DIR / "data" / "cars_v2.csv")
    assert len(v2) > len(v1)


def test_make_xy_shapes():
    """X 和 y 的条数必须一样，X 每行 3 个数字。"""
    rows = load_rows(BASE_DIR / "data" / "cars_v2.csv")
    X, y = make_xy(rows)

    assert len(X) == len(y) == len(rows)
    assert len(X[0]) == 3
