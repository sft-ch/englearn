# Englearn 网页模式容器镜像。
#
# 容器内没有桌面环境，所以关闭「划词悬浮窗」与「全局热键」，
# 只提供浏览器界面。Windows 上的完整功能请直接运行 start.cmd。

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENGL_DATA_DIR=/app/data \
    ENGL_CONFIG=/app/config/config.json

WORKDIR /app

COPY app.py ./
COPY core ./core
COPY web ./web
COPY config.example.json ./
COPY README.md ./

RUN mkdir -p /app/data /app/exports /app/config /app/logs

EXPOSE 8765

# 0.0.0.0 只在容器网络内有效；宿主机请只映射到 127.0.0.1（见 docker-compose.yml）
CMD ["python", "app.py", "--host", "0.0.0.0", "--no-popup", "--no-hotkey", "--no-open"]
