# 溯源说明（PROVENANCE.md）

回答一个问题：**这个模型是怎么来的？**

## 一条链

```text
ml/make_data.py  ──生成──▶  data/cars_v1.csv (120 行，含 4 行脏数据)
                             │
                             │ 清洗 + 补充
                             ▼
                           data/cars_v2.csv (136 行)
                             │
                             │ python -m ml.train
                             ▼
                     models/model.pkl  ←── MLflow 记录（mlruns/）
                             │
                             │ 网站加载
                             ▼
                     http://127.0.0.1:8000
```

## 每个环节的“指纹”

| 环节 | 指纹 | 记在哪 |
| --- | --- | --- |
| 代码 | git 提交号 | `models/metrics.json` 的 `git_commit`，以及 MLflow 的 `git_commit` 参数 |
| 数据 | md5 前 8 位 `c4de486c` | `models/metrics.json` 的 `dataset_hash`，以及 MLflow 的 `dataset_hash` 参数 |
| 训练参数 | `ml/configs/params.yaml` | MLflow 的 `test_size`、`random_state`、`n_estimators`、`max_depth` |
| 模型 | `models/model.pkl` | MLflow 的 Artifacts 里也存了一份 |
| 实验结果 | MAE 551 / R² 0.9933 | `models/metrics.json`、MLflow、`ml/registry/current_model.md` |

## 怎么验证一个模型是怎么来的

```powershell
# 1. 看现在线上模型的信息
Get-Content models/metrics.json

# 2. 看这个模型是哪次训练跑出来的
python -m mlflow ui
# → 打开 car-price 实验，找到 MAE = 551 的那次运行
# → 里面能看到 git_commit 和 dataset_hash

# 3. 用同样的代码和数据重新跑一次，应该得到一样的数字
git checkout <MLflow 里记的 git_commit>
python ml/make_data.py
python -m ml.train
```

如果第 3 步跑出来的 MAE 和记录不一样，说明有东西没被记录（比如忘了记某个参数）——
这正是“可复现性”要解决的问题。

## 已知的简化

为了在课程项目里保持简单，这几处做了简化，答辩时如果被问到可以这样回答：

1. **数据是脚本生成的**，不是真实交易数据（原因见 `ml/README_data.md`）。
2. **模型文件直接提交进 Git**，真实项目应该从 MLflow Registry 拉取并用版本号引用。
3. **CI 里用 `python ml/make_data.py` 重建数据**，而不是 `dvc pull`，因为 CI 没有配 DVC 远端的凭证。
4. **没有模型监控**（线上预测漂移、数据漂移），课程要求里也没有这一项。
