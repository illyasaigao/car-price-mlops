# 数据说明（README_data.md）

## 1. 数据是什么

二手车的报价数据，一行就是一辆车：

| 列名 | 含义 | 例子 | 范围 |
| --- | --- | --- | --- |
| `year` | 上牌年份 | 2020 | 1990–2026 |
| `mileage_km` | 行驶里程（公里） | 50000 | 0–500000 |
| `engine_l` | 排量（升） | 2.0 | 0.5–8.0 |
| `price_eur` | 车价（欧元） | 22376 | 1500–200000 |

共 4 列、136 行（v2）。

## 2. 数据从哪来

**来源：脚本生成的模拟数据，不是真实交易数据。**

生成脚本是 `ml/make_data.py`。它按一个简单的市场规律来造数据：

```text
价格 = 26000 × 0.9^(车龄) + 5000 × 排量 − 0.03 × 里程 + 随机波动
```

也就是：车越老越便宜（每年打九折）、排量越大越贵、里程越多越便宜。

**为什么用模拟数据？**

1. 能完全复现：任何人运行 `python ml/make_data.py`，得到的 CSV 一个字节都不差（脚本里固定了随机种子 `random.seed(7)`）。
2. 不涉及隐私和授权问题。
3. 可以故意造出脏数据，用来演示“清洗”这一步 —— v1 里那 4 行错误数据就是故意的。

真实项目里这里会换成 Kaggle / 公司数据库导出的 CSV，**流程完全一样**，只是 `make_data.py` 换成 `download.py`。

## 3. 两个版本有什么区别（v1 和 v2）

| | v1 | v2 |
| --- | --- | --- |
| 文件名 | `data/cars_v1.csv` | `data/cars_v2.csv` |
| 行数 | 120 | 136 |
| 状态 | 原始数据，末尾有 4 行错误 | 清洗 + 补充后的数据 |

v1 末尾的 4 行错误数据：

| 年份 | 里程 | 排量 | 价格 | 错在哪 |
| --- | --- | --- | --- | --- |
| 1890 | 50000 | 2.0 | 20000 | 年份不可能这么早 |
| 2018 | −500 | 2.0 | 18000 | 里程是负数 |
| 2019 | 80000 | 0.0 | 15000 | 排量是 0 |
| 2020 | 60000 | 2.0 | 999999 | 价格离谱（多了两个 9） |

v2 做了两件事：

1. **删掉**这 4 行错误数据（脏数据会让模型学歪）；
2. **补充** 20 行正常数据（原始数据太少，136 行比 120 行更稳）。

## 4. 用 DVC 管版本

```powershell
# 安装（只做一次）
pip install dvc

# 初始化（只做一次）
dvc init

# 让 DVC 管这两个文件
dvc add data/cars_v1.csv
dvc add data/cars_v2.csv
```

执行完，项目里会多出：

- `data/cars_v1.csv.dvc`、`data/cars_v2.csv.dvc` —— 两个很小的指针文件（里面只有一个哈希值），**这两个会进 Git**；
- 原始 CSV **不进 Git**（根目录 `.gitignore` 已经排除，DVC 就不再重复生成 `data/.gitignore`）；
- 真正的 CSV 被复制到 `.dvc/cache/` 里。

实际生成的指针内容（可以直接拿来讲）：

```yaml
# data/cars_v1.csv.dvc
outs:
- md5: 60c4feee9a3395029af3718015f5c95b
  size: 2729
  hash: md5
  path: cars_v1.csv
```

```yaml
# data/cars_v2.csv.dvc
outs:
- md5: c4de486c2b697f310979f62419e15e5d
  size: 3086
  hash: md5
  path: cars_v2.csv
```

**v2 的 `c4de486c` 和 `models/metrics.json` 里的 `dataset_hash` 是同一个值**，这就是“模型 ← 数据”的可追溯证据。

### 配置远端（课程要求 MS Azure）

本项目已按课程要求配置好 Azure Blob Storage 远端，实测 `dvc push` 输出 `2 files pushed`。

| 项 | 值 |
| --- | --- |
| 远端名 | `mazure`（默认远端） |
| storage account | `wut2026` |
| container | `dvc` |
| URL | `azure://dvc/car-price` |
| 凭证 | SAS 令牌，存在 `.dvc/config.local`（**被 Git 忽略，不进仓库**） |

`.dvc/config` 里只有地址和账户名，可以安全提交：

```ini
[core]
    remote = mazure
['remote "mazure"']
    url = azure://dvc/car-price
    account_name = wut2026
['remote "storage"']
    url = D:\111\dvc-storage
```

换台机器重做一遍时的完整命令：

```powershell
.\.venv\Scripts\python.exe -m pip install "dvc[azure]"
.\.venv\Scripts\python.exe -m dvc remote add -d mazure azure://dvc/car-price
.\.venv\Scripts\python.exe -m dvc remote modify mazure account_name wut2026
.\.venv\Scripts\python.exe -m dvc remote modify --local mazure sas_token "<SAS 令牌>"
.\.venv\Scripts\python.exe -m dvc push
```

**密钥为什么不进 Git**：`--local` 把凭证写进 `.dvc/config.local`，而 `.dvc/.gitignore` 里有 `/config.local`，所以它永远不会被提交。

**验证远端里真的有文件**（不需要 Azure 门户权限）：

```powershell
.\.venv\Scripts\python.exe -c "from azure.storage.blob import ContainerClient; tok=open('.dvc/config.local',encoding='utf-8').read().split('sas_token = ')[1].strip(); c=ContainerClient('https://wut2026.blob.core.windows.net','dvc',credential=tok); [print(b.name, b.size) for b in c.list_blobs(name_starts_with='car-price')]"
```

输出两行（文件名就是数据的 md5）：

```text
car-price/files/md5/60/c4feee9a3395029af3718015f5c95b 2729
car-price/files/md5/c4/de486c2b697f310979f62419e15e5d 3086
```

**本地备用远端**：仓库里还留了一个本地目录远端 `storage`（`D:\111\dvc-storage`），没网时可以用 `dvc push -r storage` 演示。

### 数据被改坏时怎么还原

```powershell
dvc status              # 会显示 modified: data\cars_v2.csv
dvc checkout --force    # 还原成登记的那一版
dvc status              # Data and pipelines are up to date.
```

不加 `--force` 时 DVC 会拒绝覆盖未保存的修改，这是保护机制。

### 版本怎么对应

| Git 提交 | 用的数据 | 说明 |
| --- | --- | --- |
| 第一次提交 | v1 | 只有原始数据，4 行错误还在 |
| 之后的提交 | v2 | 加了清洗和补充，训练改用 v2 |

用 `git log --oneline` 看提交号；用 `git show <提交号>:data/cars_v2.csv.dvc` 看当时那一版数据的哈希。
每一版数据的哈希也记在 MLflow 的参数 `dataset_hash` 里，所以能回答“这个模型是用哪版数据训的”。

## 5. 怎么检查数据是干净的

`tests/test_data_pipeline.py` 里有 4 个测试：

- v1 里确实有脏数据（证明清洗是有必要的）；
- v2 里没有任何一行超出合法范围；
- v2 的行数比 v1 多；
- `make_xy` 造出来的 X 和 y 行数一致、X 每行 3 个数字。

跑一下就知道数据有没有被改坏：

```powershell
python -m pytest tests/test_data_pipeline.py -q
```
