# 项目约定（AGENTS.md）

本文件供 AI 编码助手与开发者共同遵守。任何修改代码前请先阅读本文件。

## 项目根目录与修改基准

- 本项目开发基准目录为 `E:\xiangmu\python\wgxt002`（自 git 远程 `dev-1.003` 分支全新拉取，
  2026-08 起以此目录为准）。
- **一切代码修改、阅读、运行均以 `E:\xiangmu\python\wgxt002` 为准**，
  旧目录 `E:\xiangmu\python\wgxt001`（及更早的 `E:\xiangmu\python\wgxt`）不再使用、不要修改，
  仅作模型/数据备份。
- 目录内已存在的内容（如 `backend/lan_scan.py`、`.idea/`、`uploads/`、日志文件、截图）
  属用户自有文件，除非任务明确要求，否则不要删除或改动。

## Git 提交约定

- 代码修改完成后不需要提交 git，由开发者自行提交；AI 不主动执行 `git commit` / `git push`。
- 仅当开发者明确要求分支合并、切换分支等 git 操作时，AI 才执行相应 git 命令（如 merge、worktree、push）。
- 合并任务中涉及的新文件、未提交调试改动仍需保留在工作区，AI 只按任务要求操作 git。

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
python install_ai_deps.py   # 安装 AI 依赖（torch/transformers），自动检测 GPU，无 GPU 自动装 CPU 版
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

## Windows PowerShell 中文编码注意（防止数据乱码）

- **根因**：Windows PowerShell 5.1 向外部程序（如 `python -`）管道传输文本时按系统 ANSI/ASCII 编码，
  中文会被破坏成 `?`，导致写入数据库/文件的真实数据乱码（曾发生在 system_settings 的知识库配置上）。
- **禁止**：不要用 `@'...'@ | python -` 这类管道方式执行含中文的 Python 脚本；不要把中文字面量经
  PowerShell 管道喂给任何外部程序（curl 的 `-d` 参数同理）。
- **正确做法**：需要执行含中文的脚本/请求时，先用 apply_patch 把脚本写成 UTF-8 文件，
  再执行 `python -X utf8 脚本文件.py`；后端代码内中文文件读写统一显式 `encoding="utf-8"`。
- **排查**：终端/日志显示乱码不一定是数据乱码（可能是控制台显示编码问题）。
  判断数据是否真乱码：用 `ascii()` / `repr()` 输出转义码点检查，或直接用 UTF-8 文件脚本读取数据库原值。

## 开发方法论（Skills 驱动，所有开发任务强制遵守）

本方法论是项目功能开发的唯一执行流程。任何新功能、改动、bug 修复都必须按此执行；
每个阶段都有触发条件、必调 skill、产出物与退出标准，未达标不得进入下一阶段。

### 阶段 0：任务分类与上下文装载

- **必做**：开始任何开发前，先完整阅读本 `AGENTS.md` 与相关 `docs/` 规格文档，确认任务归属与影响范围。
- **任务分级**：
  - **小改动**（≤5 个文件且 ≤100 行、不涉及新表/新接口/权限变化）：可直接进入阶段 4 实现，但阶段 5/6/7 不可跳过。
  - **中改动**（涉及新接口、新数据表、跨模块、状态机变更）：完整走阶段 2→7。
  - **大功能/需求模糊**：先走阶段 1 澄清，再阶段 2→7。
- **skill**：`using-agent-skills` 确认本任务适用的 skill 组合，避免遗漏或重复使用。

### 阶段 1：需求澄清

- **触发**：需求模糊、存在影响结果的决策点、用户以"想一下/可不可以/你觉得呢"等开放口吻提问。
- **调用**：`interview-me`（一次一问，直到约 95% 置信度）；想法尚未定型时先用 `idea-refine` 做发散与收敛。
- **产出**：无歧义的需求结论，可直接写入阶段 2 的规格。
- **退出标准**：没有未决的关键问题，需求结论可以被写成规格。

### 阶段 2：规格设计（先规格后代码）

- **触发**：新功能、跨模块改动、涉及数据表/接口/权限模型的任何任务。
- **调用**：`spec-driven-development` 写 `docs/<功能名>_spec.md`，结构至少包含：目标、数据结构、接口契约、前端交互、成功标准。
- **接口契约**：涉及接口时同步调用 `api-and-interface-design`（REST 资源复数命名、PATCH 增量更新、分页格式、边界校验），契约先定再实现。
- **数据/权限**：涉及新表、审核状态机、权限模型时，在规格中写明并与"代码约定"第 3/7 条保持一致。
- **产出**：`docs/` 下的中文规格文档。
- **退出标准**：规格落盘，接口字段与错误语义明确，核心决策有记录。

### 阶段 3：任务拆解

- **调用**：`planning-and-task-breakdown`。
- **产出**：纵向切片清单（后端模型 → 接口 → 前端页面 → 验证），每片保持系统可运行。
- **退出标准**：切片顺序明确，每片都能独立验证。

### 阶段 4：增量实现

- **后端**：`incremental-implementation` + `test-driven-development`（先写失败用例/断言再实现）。
- **前端**：`frontend-ui-engineering`（遵循 `frontend/src/styles/tokens.css` 与 `themes.css` 设计令牌）；需要风格/组件参考时配 `ui-ux-pro-max`。
- **安全**：任何用户输入、认证授权、存储、UGC 场景调用 `security-and-hardening`（参数化查询、渲染转义、禁止直接 `v-html`）。
- **性能**：涉及查询、大列表、N+1 场景时调用 `performance-optimization`。
- **切片节奏**：单次改动超过约 5 个文件或 100 行前，必须完成当前切片验证。
- **退出标准**：当前切片完成，系统可运行。

### 阶段 5：验证（测试驱动）

- **后端**：新增接口必须在 `backend/smoke_test.py` 增加对应冒烟断言并跑通；bug 修复先写复现用例再修（`test-driven-development`）。
- **前端**：模型无视觉能力，禁止用截图判断效果；必须用 `browser-testing-with-devtools` / `chrome-devtools` / `chrome-devtools-cli` 做 DOM 审核：DOM 结构与类名挂载、computed style、CSS 变量实际取值、响应式断点布局、控制台报错。
- **专项**：`a11y-debugging`（可访问性）、`debug-optimize-lcp`（首屏性能）、`memory-leak-debugging`（内存/长列表）。
- **退出标准**：smoke 全绿，DOM 审核通过，控制台无相关报错。

### 阶段 6：评审收尾

- **调用**：`code-review-and-quality`（正确性/安全/性能/可维护性/一致性五轴）+ `code-simplification`（去重、删死代码）。
- **关键决策**：高风险的架构/安全/数据决策额外走 `doubt-driven-development` 对抗式审查。
- **检查项**：无越界改动、无死代码、注释中文、命名与项目一致、规格与代码同步。
- **退出标准**：自查通过。

### 阶段 7：记录与提交

- **调用**：`documentation-and-adrs` 同步更新规格/ADR；`git-workflow-and-versioning` 控制提交粒度与提交信息规范。
- **上线**：部署前调用 `shipping-and-launch` 走发布清单。
- **退出标准**：文档与代码一致，变更提交完成。

### Skill 速查表

| 场景 | 调用 skill | 阶段 |
| --- | --- | --- |
| 任务分类/确认适用 skill | `using-agent-skills` | 0 |
| 需求不明确/关键决策 | `interview-me` → `idea-refine` | 1 |
| 规格设计 | `spec-driven-development` | 2 |
| 接口契约设计 | `api-and-interface-design` | 2 |
| 任务拆解 | `planning-and-task-breakdown` | 3 |
| 增量实现 | `incremental-implementation` + `test-driven-development` | 4 |
| 安全加固 | `security-and-hardening` | 4 |
| 性能优化 | `performance-optimization` | 4 |
| 前端 UI 实现 | `frontend-ui-engineering`（配合 `ui-ux-pro-max`） | 4 |
| 后端冒烟/复现 | `test-driven-development` + `backend/smoke_test.py` | 5 |
| 浏览器 DOM 审核 | `browser-testing-with-devtools` / `chrome-devtools` / `chrome-devtools-cli` | 5 |
| 无障碍/首屏/内存 | `a11y-debugging` / `debug-optimize-lcp` / `memory-leak-debugging` | 5 |
| 代码评审/简化 | `code-review-and-quality` + `code-simplification` | 6 |
| 高风险决策审查 | `doubt-driven-development` | 6 |
| 文档/ADR 记录 | `documentation-and-adrs` | 7 |
| Git 提交规范 | `git-workflow-and-versioning` | 7 |
| 上线发布 | `shipping-and-launch` | 7 |

### 降级规则

- 若某个 skill 无法加载或不可用，不得跳过该阶段要求；按同阶段的人工等效步骤执行
  （如手写规格、手写 smoke 断言、手工 DOM 检查），并在交付说明中注明缺失的 skill 及补偿方式。

## 生产部署注意

- `backend/app/config.py` 的 `SECRET_KEY` 与数据库密码需通过环境变量覆盖。
- `uploads/` 目录需持久化；`BASE_URL` 需改为实际域名。
- 编辑器正文以 HTML 存储，正式环境建议接入富文本编辑器并做 XSS 过滤。
- 详细部署与二次开发说明见 `README.md`。
