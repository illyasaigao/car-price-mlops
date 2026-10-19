# 二手车价格预测（Car Price MLOps Demo）

一个很小的机器学习网站：填三个数字（年份、里程、排量），模型给出一个估价。

这个项目同时演示了课程要求的四件事：

1. **一个机器学习应用**（FastAPI 网站 + scikit-learn 模型）
2. **DevOps**（Git 分支、GitHub Actions、Docker）
3. **MLOps**（DVC 管数据、MLflow 管实验）
4. **可以复现**：任何人 clone 下来，按下面的命令就能跑出一样的结果

## 目录结构

```text
car-price-mlops/
|-- app/
|   |-- main.py              # 网站后端：3 个接口
|   `-- static/index.html    # 网页（一个表单）
|-- ml/
|   |-- make_data.py         # 生成练习数据（v1 有脏数据，v2 是清洗后的）
|   |-- data_pipeline.py     # 读 CSV，变成 X 和 y
|   |-- train.py             # 训练两个模型 + 记录到 MLflow
|   |-- configs/params.yaml  # 训练参数
|   |-- registry/current_model.md   # 现在线上用的是哪个模型
|   |-- README_data.md       # 数据说明（老师要求）
|   |-- README_experiments.md# 实验说明（老师要求）
|   `-- PROVENANCE.md        # 数据和模型的来龙去脉
|-- data/
|   |-- cars_v1.csv          # 数据集第 1 版（120 行，含 4 行错误）
|   |-- cars_v1.csv.dvc      # DVC 指针文件（运行 dvc add 后生成）
|   |-- cars_v2.csv          # 数据集第 2 版（136 行，已清洗）
|   `-- cars_v2.csv.dvc
|-- models/
|   |-- model.pkl            # 训练好的模型（线上用的就是这个）
|   `-- metrics.json         # 模型的指标
|-- tests/
|   |-- test_app.py          # 测试 1：接口
|   |-- test_model.py        # 测试 2：模型
|   `-- test_data_pipeline.py# 测试 3：数据
|-- .github/workflows/
|   |-- ci.yml               # 每次 PR：检查代码 + 跑测试 + 构建镜像
|   `-- deploy.yml           # 合并到 staging/main：构建对应环境的镜像
|-- Dockerfile
|-- requirements.txt         # 网站运行需要的包
|-- requirements-dev.txt     # 开发和训练额外需要的包
`-- README.md
```

## 怎么跑起来（Windows PowerShell）

```powershell
# 1. 建虚拟环境（用 py，不要用 python：Windows 上的 python 可能是应用商店占位程序）
py -m venv .venv
Test-Path .venv\Scripts\python.exe    # 必须输出 True

# 2. 装依赖（分三步更稳，mlflow 和 dvc 依赖多、装得慢）
.\.venv\Scripts\python.exe -m pip install fastapi uvicorn scikit-learn joblib pytest httpx ruff pyyaml
.\.venv\Scripts\python.exe -m pip install mlflow
.\.venv\Scripts\python.exe -m pip install --no-cache-dir dvc

# 或者一次装完：
# .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt

# 3. 生成数据（两份 CSV）
.\.venv\Scripts\python.exe ml\make_data.py

# 4. 训练模型（会同时写入 MLflow 记录）
.\.venv\Scripts\python.exe -m ml.train

# 5. 启动网站
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

浏览器打开 <http://127.0.0.1:8000>，填数字点“开始估价”。

## 接口

| 方法 | 地址 | 作用 |
| --- | --- | --- |
| GET | `/` | 网页 |
| GET | `/health` | 健康检查，返回 `{"status":"ok"}` |
| POST | `/api/predict` | 传三个数字，返回预测价格 |
| GET | `/api/model-info` | 返回模型指标（页面底部显示） |

请求示例：

```json
{ "year": 2020, "mileage_km": 50000, "engine_l": 2.0 }
```

返回示例：

```json
{ "predicted_price": 18345.67 }
```

字段范围：`year` **2005–2024**、`mileage_km` 0–500000、`engine_l` 0.5–8.0。
超出范围会返回 `422`，不会让脏数据进模型。

> **为什么年份只允许 2005–2024**：训练数据只覆盖这 20 年（车龄 2–21 年）。模型用了「车龄²」这个特征，二次项在训练区间内拟合得好，但**区间外会向上翘**——直接把 1990 年输进去，估出来的价格反而比 2010 年还高（外推失效）。所以接口层直接把不可信的区间挡掉，而不是返回一个看起来正常、实际错误的价格。

## 跑测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

三个测试文件分别测：**接口**（正常 + 各种非法输入，含 1990/2025 年越界）、**模型**（预测是否合理）、**数据**（v1 有脏数据、v2 干净）。共 <b>19 个测试</b>。

## Docker

```powershell
docker build -t car-price-mlops .
docker run -p 8000:8000 car-price-mlops
```

镜像里只有 `app/`、`ml/`、`models/` 和运行依赖；`tests/`、`data/`、`mlruns/` 都被 `.dockerignore` 排除了。

## MLOps 部分

### 数据版本（DVC）

```powershell
dvc init
dvc add data/cars_v1.csv
dvc add data/cars_v2.csv
dvc remote add -d storage D:\111\dvc-storage
dvc push
```

- `dvc add` 会把真正的 CSV 存进 DVC 的缓存，Git 里只留一个很小的 `.dvc` 指针文件。
- 两版数据的指纹（存在 `.dvc` 文件里）：v1 = `60c4feee…`，v2 = `c4de486c…`，和 `models/metrics.json` 里的 `dataset_hash` 对得上。
- 数据被改坏时 `dvc status` 会报 `modified`，用 `dvc checkout --force` 还原。
- 切换版本：`git checkout <提交号>` 再 `dvc checkout`；换台机器用 `dvc pull`。
- 换 Azure 远端只要改一行：`dvc remote add -d storage azure://<容器>/car-price`

> **Windows 提示**：如果 `dvc` 一运行就报 `[WinError 5] 拒绝访问: 'C:\ProgramData\iterative'`，说明 DVC 想在系统目录存配置但没有权限。用三个用户环境变量把它的目录指到自己账号下即可（不需要管理员）：
>
> ```powershell
> setx DVC_SITE_CACHE_DIR   "%LOCALAPPDATA%\dvc\site"
> setx DVC_GLOBAL_CONFIG_DIR "%LOCALAPPDATA%\dvc\config"
> setx DVC_SYSTEM_CONFIG_DIR "%LOCALAPPDATA%\dvc\system"
> ```
>
> 执行后**关掉 PowerShell 重新打开**，再跑 `dvc status`。

### 实验追踪（MLflow）

```powershell
.\.venv\Scripts\python.exe -m mlflow ui
```

浏览器打开 <http://127.0.0.1:5000>，能看到 `car-price` 实验下的三次运行：

- `linear`：线性回归（基线）
- `linear_age2`：线性回归 + 特征工程（上线）
- `forest`：随机森林

每次运行都记录了：模型类型、训练行数、**数据集哈希**、**git 提交号**、参数、MAE、R²、模型文件。

详见 `ml/README_experiments.md`。

## 分支与 CI/CD

```text
feature/*  --PR-->  dev  --PR-->  staging  --PR-->  main
```

- 往 `dev` / `staging` / `main` 提 PR，CI 会自动跑：`ruff check`（lint）→ `ruff format --check`（格式）→ `pytest`（19 个测试）→ `docker build` → 起容器测 `/health`。
- 合并到 `staging`：`deploy.yml` 用 staging 的 secrets 生成 `.env`，构建 `:staging` 镜像。
- 合并到 `main`：用生产 secrets 生成 `.env`，构建 `:latest` 和 `:sha-<提交号>` 镜像。

需要配置的 GitHub Secrets 见 `DEPLOYMENT.md`。

## 说明与取舍

- 数据是**脚本生成的模拟数据**（`ml/make_data.py`），不是真实交易数据。目的是能完全复现、不涉及隐私，并且能故意造出 v1 的脏数据来演示清洗过程。
- `models/model.pkl` 直接提交进仓库：这样 CI 和 Docker 构建不需要先重训模型。真实项目里模型应该从 MLflow Registry 拉取。
- CI 里用 `python ml/make_data.py` 重建数据，而不是 `dvc pull`：这样 CI 不需要访问 DVC 远端和云凭证。真实项目会给 CI 配置只读的远端凭证再 `dvc pull`。
- **DVC 远端已配置为 Azure Blob Storage**（课程要求）：storage account `wut2026`、container `dvc`、远端名 `mazure`，地址 `azure://dvc/car-price`，实测 `dvc push` 输出 `2 files pushed`。

  认证用的 SAS 令牌保存在 `.dvc/config.local`，该文件被 `.dvc/.gitignore` 的 `/config.local` 忽略，**不会进 Git**；`.dvc/config` 里只有地址和账户名，可以安全提交。仓库里同时保留一个本地远端 `storage`（`D:\111\dvc-storage`）作离线备用。详见 `ml/README_data.md`。
