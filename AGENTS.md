# 项目约定（AGENTS.md）

本文件供 AI 编码助手与开发者共同遵守。任何修改代码前请先阅读本文件。

## 项目根目录与修改基准

- 本项目已从 `E:\xiangmu\python\wgxt` **迁移**到 `E:\xiangmu\python\wgxt001`。
- **一切代码修改、阅读、运行均以 `E:\xiangmu\python\wgxt001` 为准**，旧目录 `E:\xiangmu\python\wgxt` 不再使用、不要修改。
- 目录内已存在的内容（如 `backend/lan_scan.py`、`.idea/`、`uploads/`、日志文件、截图）属用户自有文件，除非任务明确要求，否则不要删除或改动。

## 项目简介

前后台分离的文稿发布系统：

- 前台：新闻门户风格（栏目浏览、文章详情、搜索、点赞/收藏/转发、注册登录）
- 后台：编辑写稿、二级审核、栏目/用户/资源管理、门户模块配置、数据统计

## 技术栈

| 端 | 技术 |
| --- | --- |
| 后端 | Python FastAPI + SQLAlchemy + PyMySQL + JWT（`backend/`） |
| 前端 | Vue 3 + Vite + Pinia + Vue Router + Element Plus + ECharts（`frontend/`） |
| 数据库 | MySQL（192.168.14.216:3306，库名 `wengaofabu`，详见 `backend/app/config.py`） |

## 常用命令

```bash
# 后端：安装依赖 → 自动建库/建表/兼容迁移/种子数据与系统配置（幂等） → 启动（端口 8000，接口文档 /docs）
cd backend
python -m pip install -r requirements.txt
python init_db.py   # 若 MySQL 上无 wengaofabu 库会自动创建，可重复执行
python run.py

# 后端接口冒烟测试（验证核心业务流程，可重复执行）
python smoke_test.py

# 前端：开发模式（端口 5173，/api 与 /static 代理到 8000）
cd frontend
npm install
npm run dev
```

种子账号：管理员 `admin/admin123`、编辑 `editor/editor123`、用户 `user/user123`。

## 代码约定

1. **注释使用中文**，重要接口与业务规则必须写注释，便于二次开发。
2. **后端分层**：
   - `app/models/`：SQLAlchemy 实体（Entity）
   - `app/schemas/`：Pydantic 请求/响应校验（DTO）
   - `app/routers/`：接口路由（Controller 层）
   - `app/core/`：JWT、权限依赖、分页工具
   - `app/services/`：跨路由复用的业务逻辑（如埋点记录）；单接口逻辑简单时可留在路由函数内
3. **权限**：接口必须显式声明依赖——公开接口不注入用户；需登录用 `Depends(get_current_user)`；仅管理员用 `Depends(require_roles("admin"))`；可选登录用 `Depends(get_optional_user)`。
4. **响应格式**：成功返回 `{"message": ..., "业务数据": ...}` 或列表 `{"items": [...], "total": n, "page": p, "page_size": s}`；失败用 `raise HTTPException(状态码, "中文提示")`。
5. **事务**：一个请求一个 Session（`get_db`），多处修改通过一次 `db.commit()` 一起提交（等价 Spring `@Transactional`）。
6. **前端**：设计令牌集中在 `frontend/src/styles/tokens.css`；接口定义统一维护在 `frontend/src/api/index.js`；新增页面在 `src/views/` 下创建并注册到 `src/router/index.js`。
7. **审核状态机**（二级审核）：`draft → pending_first → pending_second → published`，任意一级可 `rejected`（退回编辑），发布后可 `offline`。改动状态机时同步更新 `articles.py` 与 `reviews.py` 中的分支逻辑，并在注释中说明。
8. **埋点**：观看/点赞/收藏/转发统一经 `app/services/event_service.py` 写入 `event_logs`；点赞/收藏去重逻辑在 `interactions.py`（`user_actions` 唯一约束）。
9. **Dify 接入**：Dify 工作流统一经 `app/services/dify_service.py` 的 `run_workflow()` 调用；工作流信息登记在 `dify_workflows` 表（后台 `/api/dify/workflows` 管理），默认配置走 `.env` 的 `DIFY_*` 变量。接入说明见 `docs/dify_guide.md`。
10. **门户主题**：前台换肤基于 CSS 变量（`frontend/src/styles/themes.css` 的 `.theme-*` 覆盖块），PortalLayout 外壳按 `portal_theme` 配置挂类；登录页与后台不换肤。新增风格需同步 `backend/app/routers/portal.py` 的 `PORTAL_THEMES`、`themes.css`、后台主题页 `themes` 数组三处。

## 前端样式修改后的验证方式（模型无视觉能力）

- 当前模型**没有视觉能力**，不能通过"看截图/看图片"判断样式是否正确；不要再依赖截图验证前端效果。
- 凡修改前端样式（布局、颜色、间距、字体、主题换肤、响应式等），必须使用 **Chrome DevTools 进行 DOM 审核**验证，检查项包括：DOM 结构与类名挂载（如门户换肤的 `.theme-*` 是否挂到 PortalLayout 外壳）、元素的 computed style（计算样式）与 CSS 变量实际取值、响应式断点下的布局、控制台是否有样式相关报错。
- 可用 skill：`chrome-devtools` / `chrome-devtools-cli`（DOM 与样式检查）、`debug-optimize-lcp`（首屏性能）、`a11y-debugging`（可访问性）；涉及换肤时同时遵守第 10 条的三处同步。

## 生产部署注意

- `backend/app/config.py` 的 `SECRET_KEY` 与数据库密码需通过环境变量覆盖。
- `uploads/` 目录需持久化；`BASE_URL` 需改为实际域名。
- 编辑器正文以 HTML 存储，正式环境建议接入富文本编辑器并做 XSS 过滤。
- 详细部署与二次开发说明见 `README.md`。
