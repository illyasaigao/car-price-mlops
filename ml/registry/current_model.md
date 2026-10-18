# 当前线上模型（registry）

> 这个文件是给人看的“现在生产环境用的是哪个模型”。
> 每次训练完、决定换模型时，手动更新这里。

## 现在用的是

| 项目 | 值 |
| --- | --- |
| 模型文件 | `models/model.pkl` |
| 实验名 | `linear_age2`（线性回归 + 特征工程） |
| 输入特征 | 车龄、里程、排量、车龄² |
| 训练数据 | `data/cars_v2.csv`（136 行，8:2 切分） |
| 数据指纹 | `c4de486c` |
| 平均误差 MAE | 551 欧元 |
| R² | 0.9933 |

## 为什么是它

三个实验里 MAE 最小：

| 实验 | MAE | R² |
| --- | --- | --- |
| linear | 1299 | 0.961 |
| **linear_age2** | **551** | **0.9933** |
| forest | 1566 | 0.926 |

## 怎么更新这个文件

1. 改 `ml/configs/params.yaml` 或 `ml/data_pipeline.py`；
2. 跑 `python -m ml.train`；
3. 看 `python -m mlflow ui` 里新的对比结果；
4. 如果新模型更好，把上面表格的数字改掉，并写清楚为什么换。

## 回滚怎么办

```powershell
# 看历史提交
git log --oneline

# 切回旧版本（代码 + 数据 + 模型一起回退）
git checkout <旧提交号>
dvc checkout
```

因为模型文件也进了 Git，所以切回旧提交就等于回到旧模型。
