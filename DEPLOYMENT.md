# 部署说明（DEPLOYMENT.md）

这个项目的“部署”分两层：

1. **CI**（`.github/workflows/ci.yml`）：每次提 PR 都跑测试 + 构建镜像。镜像能构建成功，说明代码是完整的。
2. **CD**（`.github/workflows/deploy.yml`）：合并到 `staging` 或 `main` 后，自动构建对应环境的镜像并推到 Docker Hub。

> 课程要求里写明：staging 只需要构建镜像，不要求发布流程；main 也不要求真正的部署流程。
> 所以这里做到“构建并推送镜像”就满足要求了。后面想真的部署到服务器，只需要在流水线最后加一步。

## 1. 分支流程

```text
feature/xxx  --PR-->  dev  --PR-->  staging  --PR-->  main
```

| 分支 | 用途 | 触发什么 |
| --- | --- | --- |
| `feature/*` | 开发新功能 | PR 到 dev 时跑 CI |
| `dev` | 集成分支 | PR / push 跑 CI |
| `staging` | 预发布 | 合进来后跑 `deploy.yml` 的 staging 任务 |
| `main` | 生产 | 合进来后跑 `deploy.yml` 的 production 任务 |

## 2. 在 GitHub 上要做的手工设置（只做一次）

### 2.1 保护分支

Settings → Branches → Add branch protection rule，对 `dev`、`staging`、`main` 都勾上：

- Require a pull request before merging
- Require status checks to pass before merging → 选 `测试和代码检查` 和 `构建 Docker 镜像`

这样 CI 失败时，GitHub 会直接禁止合并 —— 这就是课程要求的“CI 失败不能合并”。

### 2.2 添加 Secrets

Settings → Secrets and variables → Actions → New repository secret：

| 名字 | 内容 | 用在哪 |
| --- | --- | --- |
| `DOCKERHUB_USERNAME` | 你的 Docker Hub 用户名 | 登录 + 镜像名 |
| `DOCKERHUB_TOKEN` | Docker Hub 的 Access Token（不是密码） | 登录 |
| `STAGING_ENV` | staging 的配置，例如 `APP_ENV=staging` | 生成 `.env` |
| `PRODUCTION_ENV` | 生产的配置 | 生成 `.env` |

Docker Hub Token 在这里生成：Docker Hub → Account settings → Security → New Access Token（权限选 Read & Write）。

### 2.3 打开 Actions

仓库页面 → Actions 标签 → 如果提示，点 “I understand my workflows, go ahead and enable them”。

## 3. 流水线每一步在做什么

### ci.yml

| 步骤 | 作用 |
| --- | --- |
| checkout | 把代码拉到 CI 机器 |
| setup-python | 装 Python 3.12 |
| pip install | 装 `requirements-dev.txt` |
| make_data | 重建两份 CSV（CI 不连 DVC 远端） |
| ruff check | 代码检查（lint：未使用变量、语法隐患等），有错误就失败 |
| ruff format --check | 代码格式检查（相当于 black 的作用），格式不统一就失败 |
| pytest | 跑所有测试，有失败就失败 |
| docker build | 构建镜像，失败就失败 |
| docker run + curl | 真起一个容器，请求 `/health`，确认服务能跑 |

### deploy.yml

| 环境 | 触发 | 做的事 |
| --- | --- | --- |
| staging | push 到 `staging` | 用 `STAGING_ENV` 生成 `.env` → 构建 `:staging` 镜像 → 推送 |
| production | push 到 `main` | 用 `PRODUCTION_ENV` 生成 `.env` → 构建 `:latest` 和 `:sha-<提交号>` → 推送 |

`:sha-<提交号>` 这个标签很重要：任何一次上线都能对应到唯一的代码版本，出问题能精确回滚。

## 4. 本地模拟一次“部署”

想在没有 GitHub 的情况下证明这条链路能通，可以本地执行：

```powershell
# 造 .env
"APP_ENV=staging" | Out-File -Encoding utf8 .env

# 构建 staging 镜像
docker build --build-arg APP_ENV=staging -t car-price-mlops:staging .

# 跑起来
docker run -p 8000:8000 car-price-mlops:staging

# 验证
curl http://127.0.0.1:8000/health
```

## 5. 常见问题

**Q：Actions 报 permission denied / 403？**
A：检查 Secrets 名字是否拼对，Token 是否有 Read & Write 权限。

**Q：docker build 在 CI 里很慢？**
A：第一次会拉基础镜像 `python:3.12-slim`，之后会走缓存。可以加 `docker/setup-buildx-action` 提速，但不是必须的。

**Q：为什么不把镜像推到 GitHub Container Registry（ghcr.io）？**
A：可以，把 `docker/login-action` 的 registry 换成 `ghcr.io`、用户名换成 `${{ github.actor }}`、密码换成 `${{ secrets.GITHUB_TOKEN }}` 就行。用 Docker Hub 只是因为它最常见。
