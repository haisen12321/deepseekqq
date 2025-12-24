# deepseek_qq_bot_istoreos

面向 iStoreOS（OpenWrt 系）部署的 DeepSeek QQ 群聊机器人，使用 NapCatQQ/OneBot v11（HTTP API）接收事件并回调发送消息。支持“群内共享上下文”（同群共享历史）。

## 特性

- 仅依赖纯 Python 包：`python-dotenv` + `requests` + `filelock`
- 标准库 HTTP Server：`POST /onebot/event`、`GET /health`
- 群内共享上下文（按 group_id 维护），持久化到 JSON 文件
- 触发规则：@机器人 或 `/ai` 前缀（可配置）
- 指令：`/help` `/ping` `/reset`
- 速率限制：10 秒内最多回复一次
- 回复自动分段（>1500 字拆分发送）

## 目录结构

```
deepseek_qq_bot_istoreos/
  app/
    __init__.py
    server.py
    config.py
    deepseek_client.py
    onebot_client.py
    context_store.py
    handlers.py
    utils.py
  data/
  deploy/
    Dockerfile
    docker-compose.yml
    run.sh
  .env.example
  requirements.txt
  README.md
```

## 配置说明（.env）

复制 `.env.example` 为 `.env` 并填写：

- `DEEPSEEK_API_KEY`（必填）
- `DEEPSEEK_BASE_URL`（默认 `https://api.deepseek.com`）
- `DEEPSEEK_MODEL`（默认 `deepseek-chat`）
- `ONEBOT_BASE_URL`（必填，例如 `http://127.0.0.1:3000`）
- `ONEBOT_ACCESS_TOKEN`（可选，OneBot token）
- `SINGLE_GROUP_ID`（必填，仅该群生效）
- `REQUIRE_AT`（默认 `true`）
- `BOT_SELF_ID`（可选，机器人 QQ 号）
- `MAX_TURNS`（默认 `12`）
- `STORAGE_PATH`（默认 `./data/state.json`）
- `LOG_LEVEL`（默认 `INFO`）
- `PORT`（默认 `8080`）

> OneBot 认证常见方式是在请求头加 `Authorization: Bearer <token>`，本项目已支持。部分 OneBot 也支持在 URL 参数中传递 token，可按 NapCat 配置。

## 运行方式 A：Docker（推荐）

1. 在 iStoreOS 中安装 Docker/容器插件。
2. 进入项目目录，复制环境文件：

```bash
cp .env.example .env
```

3. 编辑 `.env`。
4. 启动容器：

```bash
cd deploy
docker compose up -d --build
```

5. 验证健康检查：

```bash
curl http://<设备IP>:8080/health
```

## 运行方式 B：本地 Python（尽量轻量）

> 建议安装 python3 与 pip，如果环境支持可使用 venv。

```bash
opkg update
opkg install python3 python3-pip
```

在项目根目录执行：

```bash
cp .env.example .env
pip3 install -r requirements.txt
python -m app.server
```

也可以使用脚本：

```bash
sh deploy/run.sh
```

## NapCat/OneBot 回调配置

在 NapCatQQ / OneBot v11 配置回调地址：

```
http://<设备IP>:8080/onebot/event
```

## 触发方式

- `@机器人` 或 `/ai 问题内容`（默认 `REQUIRE_AT=true`）
- 指令：
  - `/help`：帮助
  - `/ping`：pong
  - `/reset`：清空本群共享上下文

## 常见问题排查

- **收不到事件**：检查回调 URL、端口映射、防火墙，同网段可先本地 curl 测试。
- **只对一个群生效**：检查 `SINGLE_GROUP_ID` 是否为正确群号。
- **@识别失败**：OneBot 事件可能只有 `raw_message`，检查消息段 `message` 是否包含 `at`，或使用 `/ai` 触发。
- **DeepSeek 报 401/429/5xx**：检查 API Key、是否触发限速、服务是否可用。

## HTTP 接口

- `POST /onebot/event`：接收 OneBot 事件回调（始终返回 200）
- `GET /health`：返回 `ok`

## 许可

默认未指定，可根据需求自行添加 LICENSE。
