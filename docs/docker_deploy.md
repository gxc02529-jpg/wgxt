# Docker 部署指南（国内镜像加速）

前后端分离部署：**前端（Nginx）→ 后端（FastAPI）→ 你已有的 MySQL**，一个 `docker compose up` 即可拉起。
镜像内已配置国内加速：pip（清华源）、apt（清华源）、npm（npmmirror）。

## 一、文件清单

| 文件 | 作用 |
| --- | --- |
| `backend/Dockerfile` | 后端镜像：Python 3.10.20 + FastAPI +（可选）AI 依赖 |
| `backend/docker-entrypoint.sh` | 启动入口：等待 MySQL → 幂等 `init_db.py` → uvicorn |
| `backend/.dockerignore` | 排除 `.env`/`uploads`/日志等，避免敏感文件进镜像 |
| `frontend/Dockerfile` | 前端镜像：Node 构建 + Nginx 托管（多阶段） |
| `frontend/nginx.conf` | Nginx：SPA 路由 + `/api`、`/static` 反代到后端 |
| `frontend/.dockerignore` | 排除 node_modules / dist |
| `docker-compose.yml` | 编排：backend + frontend（**使用已有 MySQL，不内置数据库**） |

## 二、快速开始

```bash
# 1. 准备环境变量（可选，不建 .env 则用 compose 内默认值）
#    在项目根目录创建 .env，按需覆盖：
cat > .env <<'EOF'
# 生产务必修改
SECRET_KEY=请改成随机长字符串
# 你已有的 MySQL 连接信息（必填）
DB_HOST=你的MySQL地址
DB_PORT=3306
DB_USER=root
DB_PASSWORD=你的数据库密码
DB_NAME=wengaofabu
BASE_URL=http://你的域名或IP
EOF

# 2. 构建并启动（首次构建会下载依赖，耗时较长）
docker compose up -d --build

# 3. 查看状态与日志
docker compose ps
docker compose logs -f backend

# 4. 访问
#    前端：http://服务器IP/（80 端口）
#    后端接口文档：http://服务器IP:8000/docs（若未对外映射 8000 则通过 docker exec 查看）
```

种子账号（由 `init_db.py` 创建）：管理员 `admin/admin123`、编辑 `editor/editor123`、用户 `user/user123`。

## 三、镜像体积与 AI 依赖

- 后端默认安装 **CPU 版 torch + transformers + sentence-transformers**（embedding/分类/向量化需要），镜像较大（数 GB）。
- 不需要 AI 功能时可跳过以大幅减小镜像：

```bash
docker compose build --build-arg INSTALL_AI_DEPS=false backend
```

- torch CPU 由项目脚本从 PyTorch 官方 CPU 源安装；若服务器访问 `download.pytorch.org` 慢，
  可改为阿里云 PyTorch 镜像（把 `backend/Dockerfile` 中对应 RUN 替换为）：

```dockerfile
# 先装 CPU torch（阿里云镜像），脚本检测到已装会跳过并只装 transformers
RUN pip install torch --index-url https://mirrors.aliyun.com/pytorch-wheels/cpu \
    && python install_ai_deps.py --cpu
```

### 可选：GPU 加速

CPU 版即可跑通；若要 GPU 推理，需使用 NVIDIA 容器运行时（`nvidia-container-toolkit`），
在 `docker-compose.yml` 的 backend 服务加：

```yaml
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
```

并把 `backend/Dockerfile` 中 AI 依赖改为 `python install_ai_deps.py --gpu`（构建机需能访问 GPU 或改为运行时安装）。

## 四、数据库

- 项目**使用你已有的 MySQL**，不内置数据库容器。连接信息在项目根目录 `.env` 中配置：
  `DB_HOST`（地址）、`DB_PORT`、`DB_USER`、`DB_PASSWORD`、`DB_NAME`（默认 `wengaofabu`）。
- 后端每次启动都会执行幂等 `init_db.py`：
  - 若 `wengaofabu` 库不存在且账号有 CREATE 权限，会自动建库（utf8mb4）；
  - 随后建表、兼容迁移、写入种子数据（管理员 `admin/admin123` 等），可安全重复执行。
- 若 MySQL 账号没有建库权限，请先手动创建数据库：`CREATE DATABASE wengaofabu DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
- 如需把开发环境数据带过来，可用 `mysqldump` 导出后导入该库。

## 五、必须修改的配置（生产）

| 配置 | 位置 | 说明 |
| --- | --- | --- |
| `SECRET_KEY` | `.env` → compose | JWT 签名密钥，必须改成随机长字符串 |
| `DB_PASSWORD` | `.env` → compose | 你已有 MySQL 的数据库密码 |
| `BASE_URL` | `.env` → compose | 静态资源完整 URL 前缀，改为 `http://域名` 或 `http://IP` |
| 端口 | compose `ports` | 如 80 被占用可改为 `8080:80` |

## 六、数据持久化

- 上传文件：`./uploads` 目录挂载到容器 `/app/uploads`，**不会被容器重建清空**。
## 七、AI 模型权重（如缺少）

- 本地 embedding 模型 `backend/app/multilingual-e5-small` 已在仓库内，随镜像复制。
- 标题分类模型与向量化模型权重不在仓库（见 `backend/app/aimodel/model/`、
  `backend/app/aiVectorizationModel/model/`）。如有权重文件，放到对应目录后重新构建，
  或在 compose 中额外挂载卷。缺失时 AI 分类/向量化功能会报错，其余功能不受影响。

## 八、常用运维命令

```bash
docker compose ps                 # 查看状态
docker compose logs -f backend    # 后端日志
docker compose logs -f frontend   # 前端/Nginx 日志
docker compose exec backend python init_db.py   # 手动重新初始化（幂等）
docker compose restart backend    # 重启后端
docker compose down               # 停止并删除容器（数据卷保留）
docker compose down -v            # 停止并删除容器+匿名卷（慎用；uploads 在宿主机目录不受影响）
```
