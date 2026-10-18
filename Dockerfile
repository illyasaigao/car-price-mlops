FROM python:3.12-slim

WORKDIR /app

# 先复制依赖清单再安装，这样改代码时不用重新装依赖（Docker 分层缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 只复制运行需要的东西
COPY app ./app
COPY ml ./ml
COPY models ./models

# 部署流水线会传 staging / production 进来，本地构建默认 local
ARG APP_ENV=local
ENV APP_ENV=$APP_ENV

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
