# MisePort 开发计划（中文版）v1.5

**制定日期：2026 年 10 月 29 日（日本时间）**
**目标发布日期：2026 年 11 月 10 日**
**文件性质：内部开发计划（INTERNAL / RELEASE EXCLUDE）**

> **发布前必须清理本文件。** 本计划服务于项目开发管理，11 月 10 日正式发布时不得进入 GitHub Release 所对应的源码 Tag、自动源码压缩包、Python 源码分发包、Windows 安装包或商家发布包。应在公开分支删除本文件，并以精简的公开 Roadmap、使用手册与 Release Notes 代替。已经进入公开 Git 历史的内容，不会因为删除最新版本而自动从历史中消失。详见 [发布内容分类规范](RELEASE_PUBLICATION_POLICY.ja.md) 和 [Issue #10](https://github.com/Siyuan-chat/miseport/issues/10)。

本项目**内部研发讨论、计划、技术方案、任务管理默认使用中文**；面向日本商家的 README、操作手顺书、界面、FAQ、视频字幕使用**日语**；国际开发者文档保留**英文**。

## 第一轮开发实际结果（2026 年 10 月 29 日）

> **第一轮代码已经合并进 main，仍是 Alpha；这不等于商家正式版或真实店铺验收。**

- **GitHub 分支：** [feat/merchant-sprint-01](https://github.com/Siyuan-chat/miseport/tree/feat/merchant-sprint-01)
- **已合并代码：** [PR #14](https://github.com/Siyuan-chat/miseport/pull/14)（14 个文件，包括 Python BASE API、商品 Mapper、日语 GUI、Cloudflare 商家 MCP/REST、打包和测试）
- **S1-01 / S1-02：** BASE v2 β 商品的只读分页、异常与安全处理及普通商品/变体映射，**模拟 API 测试通过**。未在有授权的实际 BASE 店铺调用。
- **S1-03：** 已实现本地日语 GUI 的连接/查看/审计/JSON/商家 ZIP 导出原型。**Windows Alpha EXE 构建已成功**，但实际 Windows 桌面操作、普通店主验收及签名未完成。
- **S1-04：** 架空商品生成商家专属 Cloudflare Pages ZIP，Node 测试已调用生成的 HTTP MCP initialize、tools/list、tools/call、报价与 JSON-LD。**尚未在实际商家自有域名部署**。
- **S1-05：** 发布归档敏感信息/内部文件审核工具已实现；第二轮已将 Python sdist 改为公开文件白名单并移出历史 Fixtures。**但 GitHub Tag 自动源码归档中仍存在内部工作文档与旧资产，须在 Tag 前清理（Issue #10）。**
- **S1-06：** [日语 GUI Alpha 操作说明](https://github.com/Siyuan-chat/miseport/blob/feat/merchant-sprint-01/docs/merchant/GUI_ALPHA_GUIDE.ja.md)已编写，真实演示视频尚未录制。

**CI 证据：** [完整矩阵 8/8 通过，Python 167 项测试通过](https://github.com/Siyuan-chat/miseport/actions/runs/40806005768)；[Windows Alpha 编译通过](https://github.com/Siyuan-chat/miseport/actions/runs/40806005935)。以上为代码和模拟数据验证。

**11/10 仍有硬性阻断项：** 真实商店参与和读取/展示授权 [#9](https://github.com/Siyuan-chat/miseport/issues/9)；BASE 商品公开 URL 的批量自动核验 [#13](https://github.com/Siyuan-chat/miseport/issues/13)；真正可供商家独立使用的 Windows GUI / 云端部署验收；正式发布前内部资料清理 [#10](https://github.com/Siyuan-chat/miseport/issues/10)。严禁将当前 Alpha 等同于商家正式版。

## 已合并的进一步架构进度（2026 年 10 月 29 日）

| PR | 代码状态 | 本次真正新增的能力 | 尚未证明 |
|---|---|---|---|
| [#14](https://github.com/Siyuan-chat/miseport/pull/14) | **已合并 main** · `64a07f3b` | BASE API v2β 只读客户端与商品映射、日语本地 GUI、商家 MCP/REST ZIP 原型、Windows Alpha 构建与测试 | 真实 BASE 授权、店主使用、部署和视频 |
| [#15](https://github.com/Siyuan-chat/miseport/pull/15) | **已合并 main** · `5772320b` | 根据店主确认的一个 BASE 商品页批量生成其余**候选 URL**；商品新增/变化/删除差分、旧快照安全保留；只读 Adapter 接口；Python sdist 公开白名单 | 候选 URL 逐条公网验证、GitHub Tag 的历史/内部文件清理 |
| [#16](https://github.com/Siyuan-chat/miseport/pull/16) | **已合并 main** · `60d626d7` | BASE 商品 CSV（UTF-8/CP932）与 Shopify 新旧商品 CSV 的本地**只读 Alpha 导入**；接入同一个日语 GUI；多地点库存保留未知、JPY 由店主确认 | 真实商家 CSV 兼容、复杂字段和多平台写回（不在初期范围） |

**自动测试证据：** [PR #15 的 8/8 CI、Python 208 项测试通过](https://github.com/Siyuan-chat/miseport/actions/runs/40810437650)；[PR #16 代码 CI 8/8 通过（Python 229 项测试通过）](https://github.com/Siyuan-chat/miseport/actions/runs/40811628035)，[Windows Alpha EXE 构建成功](https://github.com/Siyuan-chat/miseport/actions/runs/40811628053)。这些是 **Mock/代码层面**的验证，不是商业生产环境安全审查、Windows 实际操作或已取得真实商家同意。

**后续无真实账号即可开发：** 在独立分支 [feat/merchant-bundle-preflight](https://github.com/Siyuan-chat/miseport/tree/feat/merchant-bundle-preflight) 开展 ZIP 离线完整性、Worker 与商品一致性、域名/Manifest/hash 检查，生成失败时不覆盖上一个完整发布包。**这一批的最终测试与合并状态以对应 PR/CI 为准，不要提前标记 RELEASED。**

**仍必须留到实际商家验收：** BASE 真正读取权、公开商品 URL 的实际可访问性、真实 Windows 点击操作、商家自控 Cloudflare 公网 MCP、Meta Muse 实际商品调用、公开授权案例和视频。

## 一、目标与不可妥协的验收标准

**MisePort 是免费优先、开源、商家自主管理商品数据的 Agent Commerce 工具，不是集中式比价平台。** 用户无需编写代码，通过自己的店铺账号授权读取商品，经审核后生成供 Muse 等 AI Agent 使用的公开商品数据与接口。

**11 月 10 日必须努力交付的是「商家可以实际使用的版本」，而不是只有 Python、MCP 或架空商品的开发者 Demo。** 最低要求：

1. **真实 BASE 店铺 API 读取：** 店主使用官方只读授权（BASE API v2 β 的 items.read 等必要权限），可以自动拉取自己的已公开商品，支持分页、错误处理、手动重新同步。CSV 不能替代这一核心验收。
2. **日语无代码界面：** 普通日本店主能够在 Windows 上启动程序，通过点击完成「连接 → 导入 → 核查 → 导出」，日常操作不要求 Git、Python、Docker 或命令行。
3. **正确的数据处理：** 保留店铺标识、商品与 SKU/变体、价格、税、运费、库存状态、原始商品链接、来源、更新时间。未知信息不编造；内部或未上架商品不得误发布。
4. **商家独立发布：** 能生成仅包含获准公开商品的部署包，并在商家掌控或明确授权的 HTTPS 地址上运行只读 MCP/REST 服务。真实公网地址与原有架空 Demo 地址相互独立。
5. **至少一家真实日本商家案例：** 争取一家正在经营的日本 EC 商店正式参与，在分别同意数据读取、店铺名称/商品/图片/视频公开之后，发布真实商品与 Agent 查询的端到端案例。合成测试店或未经许可的抓取不能算作真实案例。
6. **完整日语手顺书和真实视频：** 使用实际可操作界面的截图、步骤、授权和撤销说明，制作日语字幕的录屏 Demo，不得将设计稿冒充完成的产品。
7. **正式可复现发布：** GitHub Release、可使用的 Windows 安装/运行包、源码、版本与校验和、CI 测试、已知限制和许可证清晰；不能将内部开发文件、令牌或未授权商家资料带入正式发布物。

**截至 2026-10-29 已验证的基础：** GitHub 公共仓库、Python 商品数据核心、CSV/JSON 导入、基本审计和 JSON-LD、七个只读 MCP 工具、Cloudflare 架空商品 Demo，以及一个 Muse 账号内的 Custom Connector 工具调用记录。**真实 BASE 自动读取、无代码 GUI、商家独立发布、Windows 商家安装包、真实商家公开案例均尚未完成**。不能混用“已规划、已实现、已测试、已发布”状态。

## 二、产品的实际工作流程

**主路径：**

店主打开 MisePort 日语程序 → 选择 BASE → 在自己的可信环境配置官方只读 PAT → 验证连接 → 自动读取已上架商品与变体 → 检查商品字段、公开范围、证据和时间 → 生成标准商品目录、JSON-LD 及商家发布包 → 在商家管理的 Cloudflare Pages 等位置发布 → 让支持的 Agent 连接并核对商品。

**始终保留的备用路径：** 官方平台商品 CSV/JSON → 上传/选择文件 → 数据字段自动匹配 → 相同审核与输出流程。API 是优先方案，CSV 是兜底方案。

**可选兼容路径：** 商家使用自己配置的 Agent 或其他官方 API Connector 获取授权商品，再按照 MisePort 的版本化 Canonical Catalog 输入。使用 MisePort 不应强制购买大模型 API，也不强制商家交出后台密码。

**发布边界：** 当前不提供自动下单、付款、订单读取或修改店铺商品。API Key 和 PAT 不进入公开 MisePort 网站、网页静态代码、导出文件、GitHub Issue 或演示视频。保持商家单独拥有数据与公开 URL，不建设中央商家商品数据库。

## 三、软件架构与技术约束

| 模块 | 具体实现方向 | 优先级与验收 |
|---|---|---|
| BASE Source Adapter | Python 只读 HTTP 客户端、Bearer PAT、公开商品分页、必要的变体读取、异常与限流处理；HTTP 传输可模拟 | **P0**。真实店铺读取与模拟异常测试分别留证 |
| Canonical Catalog | 复用既有商品验证与数据契约，必要时显式提升 Schema 版本；确保变体身份、可售状态与未确认字段不丢失 | **P0**。来源/价格/库存与后台一致 |
| 日本语 GUI | 优先评估原生轻量 GUI（例如 tkinter/ttk）与受保护的本地浏览器界面；以容易安装、安全、性能轻量作为选型依据 | **P0**。Windows 用户点击即可操作 |
| 本地凭证处理 | 初期优先只在进程会话中暂存 PAT、关闭后清除；持久保存仅在 OS 安全凭证库充分验证后启用 | **P0**。禁止明文落盘和公网泄露 |
| 商家专属 Exporter | JSON、JSON-LD、商品目录版本/Manifest、公开范围过滤，以及独立的只读 MCP/REST 运行包 | **P0**。部署/更新/撤回流程实际验证 |
| Muse / GEO | Tool 描述、商品结构化数据、出典、条件匹配；区分已连接工具的读取与未连接时的自然搜索 | **P0：已连接端到端；P1：自然 GEO 系统测量** |
| 平台兼容扩展 | BASE/Shopify/makeshop/カラーミー/EC-CUBE 官方 CSV 输入输出配置与后续 API Adapter | **P1**。逐平台测试，不宣称全部原生支持 |
| 分发与保真 | CI、Windows 构建、敏感信息扫描、Release 打包白名单、说明书、字幕录屏 | **P0**。Tag 和各类安装包都需检查 |

**安全要求：** 只读商品 API、仅访问授权的官方主机；未经同意不读取顾客/订单；授权失效与 API 429/5xx、网络中断时有明确错误；部分分页失败不得覆盖原本正确的商品快照；草稿、下架、私人商品默认不发布；即使已有产品描述包含提示词，也视为商品数据而非系统指令。

**BASE API β 需按最新官方文档逐项核验：** 商品列表、公开过滤条件、分页、变体、时间字段、PAT 有效期和必要权限。API 的实际可用性必须以取得授权的店铺实测为准。

## 四、开发排期（2026/10/29—11/10）

| 日期（日本时间） | 开发重点 | 达成判定 |
|---|---|---|
| **10/29** | 冻结商家可用版 P0；现有 Core/API/Cloudflare 盘点；建立第一轮开发分支与 Issue；准备真实商家招募说明 | 本计划和 Sprint 任务可执行，明确未完成事项 |
| **10/30** | BASE 只读 API 模拟客户端、分页/错误测试；GUI 技术方案；商家发布包数据契约 | 通过模拟测试，凭证安全方案可解释 |
| **10/31–11/1** | BASE 真实授权读取、商品变体映射、日语 GUI 最小流程；同步争取真实商家与分项公开授权 | 能在获得许可的商家 API 中真实获取商品；未获权限时明确阻断 |
| **11/2–11/3** | 公开商品过滤、数据审计、手动重新同步、CSV 备用方式、失败回滚 | 正确显示价格、库存、未知信息；失败不覆盖旧有效数据 |
| **11/4–11/5** | 商家专用 JSON/JSON-LD 与 MCP/REST ZIP；在独立 HTTPS 位置部署、更新、停止 | 使用获得授权的真实商品，外部 MCP 可以调用 |
| **11/6–11/7** | Windows 可启动安装包；日语实际截图手顺书、字幕视频；安全与版权审查 | 非技术用户无需终端即可使用，视频展示真实界面 |
| **11/8–11/9** | 实际店主/非技术人员端到端测试、Muse Agent 调用、修复阻断错误；商家确认最终公开案例；Release 文件清理 | P0 合格证据、真实店铺最终许可、CI 通过 |
| **11/10** | 形成正式 GitHub Release、商家下载包、完整日语指南和一份真实授权商家 Demo | 只有通过实际验收的功能才宣传“已支持” |

**真实商家招募必须与代码开发并行。** 目标在 10/31 前联系适当候选、11/1 前争取正式确认 1 家商家；截至本计划制定时还没有已确认的合作店。这属于外部依赖，不能无条件保证其按期参与。

## 五、第一轮开发 Sprint 1（10/29—11/1）

**工作分支：** [feat/merchant-sprint-01](https://github.com/Siyuan-chat/miseport/tree/feat/merchant-sprint-01)  
**跟踪 Issue：** [#12 — 首轮 BASE → GUI → 商品发布包](https://github.com/Siyuan-chat/miseport/issues/12)

| 任务 ID | 我可以完成的具体代码工作 | 验收证据 |
|---|---|---|
| **S1-01** | 编写 BASE 只读 API Client：可注入的 HTTP、官方固定主机、公开商品查询、limit/offset、401/403/429/超时/不完整响应 | 使用合成 Fixture 的测试和 CI，无须真实 PAT |
| **S1-02** | 编写 BASE 商品/变体到 MisePort Catalog 的 Mapper，价格/库存/来源/公开状态校验 | 所有转换均可回溯，未知信息不变造，非公开产品排除 |
| **S1-03** | 实现日语本地最小 GUI：连接、商品查看、审核、输出；评估原生 GUI 和本地浏览器方案 | 实际能运行的界面、模拟读取联调、Windows 打包可行性 |
| **S1-04** | 商家专用部署包构建器原型：公开目录、JSON-LD、只读 MCP/REST、Manifest/校验和 | 用合成商品生成 ZIP，确认无秘密和非公开数据 |
| **S1-05** | 现有测试回归、敏感信息扫描、正式分发文件白名单及历史测试 Fixture 迁移设计 | CI 结果和 Release 文件审核，避免开发文档泄漏 |
| **S1-06** | 制作日语 UI 文案/手顺书原型、Muse 已连接 E1 场景、自然发现 E2 基准设计和录屏脚本 | 可执行的评测用例，文字不把计划功能写成已上线 |

**建议实际实现顺序：S1-01 → S1-02 → S1-03；S1-04/05 可以并行准备。** Sprint 任务的建立并不代表代码已完成。完成后要附真实源代码变更、测试结果和未完成清单。

### 我能直接执行的任务

- GitHub 代码分支、Issue、Pull Request、开源 README 和开发文档调整。
- Python/JavaScript API 客户端、商品映射、模拟测试、CLI/GUI 原型、打包脚本与 CI。
- 商品 Schema/测试 Fixture、MCP/REST 接口、GEO 检查和复现用例。
- 发布物内容审查、敏感信息扫描、日语手顺书与视频脚本。
- 在拥有可用测试权限的环境中进行对应技术验收，并保存可公开的脱敏记录。

### 需要用户和真实商家共同完成的任务

- 寻找并联系实际经营的日本 EC 店铺；得到**数据读取、店铺识别、图片、视频和公开案例各自的许可**。
- 由店主自己在可信环境中生成/管理 BASE API PAT，不要在聊天、GitHub 或公开视频中提供。
- 实际商家后台/API 测试、商家控制的 Cloudflare 账号部署许可、Windows 非技术用户的亲手操作验证。
- 真实 Demo 的最终确认、官网/外部社区投稿和域名购买授权。

**没有商家参与时仍可完成模拟客户端与代码；但不能宣称已经完成真实商家可用版验收。**

## 六、Muse 与个人 Agent 的 GEO 验收

将“能够连接”、“能够被发现”和“被推荐”分别测试：

| 评估 | 条件 | 记录内容 |
|---|---|---|
| **E1 已连接工具** | 用户或 Muse 明确配置本店 MisePort MCP | initialize、tools/list、tools/call、正确商品、来源、未知数据、运行错误 |
| **E2 自然发现** | 没有安装本店 Connector，使用普通日语购物问题 | Agent 是否发现商品原始页面、官方商品渠道、是否正确引用；多次重复，不把偶然提及当作稳定排名 |
| **E3 目录发现** | Meta 公开 Connector 申请及审核（单独授权） | 申请、审核、批准、出现在目录、实际被使用各自独立记录 |

**11/10 最先保证 E1 和真实商家的 MCP 可用。** E2 要做基准测试，但不以影响 Muse 不公开的自然排序算法作为发布前提。现有已完成的 Muse 测试只覆盖一个账号中的架空商品 Custom Connector，不能等同于真实商家 GEO 成果。

详见 [Muse 接入机制](MUSE_CONNECT.ja.md) 与 [Agent GEO 指南](AGENT_GEO.ja.md)。

## 七、正式 Release 前内部文件清理

**本文件和内部工作资料不得进入 11/10 的正式公开 Tag。** 需要在制作 Tag 前完成：

1. 将 DEVELOPMENT_PLAN、RELEASE_2026-11-10、PROJECT_STATUS、RELEASE_CHECKLIST、商家 Pilot 招募/授权内部记录、视频录制脚本、旧品牌候选、旧 Legacy Archive 等从正式发布分支删除或转换为明确公开版，并将需要保留的内部资料放入已获授权的私有工作位置。
2. 用公开的日语操作手册、产品说明、精简 Roadmap、Release Notes、可复现测试代替内部工作文档，修正全部相对链接。
3. 修改当前会递归收进 docs、references 和 PROJECT_STATUS 的 **MANIFEST.in** 与旧 GitHub ZIP 脚本，改成明确的公开文件白名单，并检查 Tag 自动源码档案、sdist、wheel、Windows 下载包和商家发布 ZIP 的文件清单与哈希。
4. 不把真实商家的联系方式、未授权图像、私有数据或 API Token 记入仓库。曾经公开提交过的资料即使从 main 删除也会保留历史记录；如发现实际秘密还须失效凭证并处理历史泄露问题。

完整分类在 [发布清理策略](RELEASE_PUBLICATION_POLICY.ja.md)、任务 [Issue #10](https://github.com/Siyuan-chat/miseport/issues/10)。

## 八、最终判定与后续范围

**11/10 只有在关键 P0 的真实运行、商家授权、日语非技术用户体验、真实 Agent E1、可下载运行包、真实商家公开案例和分发安全全部达标后，才能宣称“商家可用版发布完成”。**

如果某项因 API 变更、店主没有授权、Cloudflare 部署或 Windows 实机问题而失败，要记录准确的阻断项，继续优先修复；不得用旧架空 Demo、概念视频或只读 CSV 代替真实商家 API 验收。

**11/10 之后再做：** Shopify/makeshop/カラーミー/EC-CUBE 的原生 API 扩充；跨平台官方 CSV 导入和经实机验证的 CSV 导出；无人工定时同步、Webhook、更多 GEO 评测和社区营销。保持中立统一 Schema、免费开源和商家自有数据，不转成中央商品聚合商。

相关文件：[商店可用版硬性验收](RELEASE_2026-11-10.ja.md) · [商家试点执行要求](merchant/PILOT_2026-11-10.ja.md) · [BASE/API 权限架构](CONNECTOR_ARCHITECTURE.ja.md) · [平台兼容矩阵](PLATFORM_COMPATIBILITY.ja.md) · [日本商家手顺书](merchant/SETUP_GUIDE.ja.md) · [GitHub Sprint #12](https://github.com/Siyuan-chat/miseport/issues/12)。

**文件状态：开发计划已更新，不代表本轮 API Connector、日语 GUI、真实商家部署或公开视频已经完成。**
