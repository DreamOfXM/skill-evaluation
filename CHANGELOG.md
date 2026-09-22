# Changelog

> **作者：DreamOfXM**（2026-09-21 起本地所有，含全部重写内容）。
> 本地演化记录。本 skill 原以 `agent-evaluation` 之名从 ClawHub 安装（registry 1.0.0，2026-02 空壳版），
> 本地重写后于 2.0.0 更名 **skill-evaluation**、删除 `.clawhub` 安装记录，与注册表彻底断开——
> ClawHub 上的 agent-evaluation 是与本 skill 无关的旧空壳，重装/升级那个名字不会再碰到这里。
> 真源：`~/.agents/skills/skill-evaluation/`（OpenClaw 侧为软链）。

- **2.3.0（2026-09-21，八评）**：①抽公共层 `scripts/_common.py`（schema 校验、容错读取、(case_id, rep) 去重与跳号检查、kappa 公式单一真源）——八评实测两脚本公共行 65、去重告警只在一侧存在，正是拷贝分叉的产物；②flaky_report 补 dup/gap 卫生告警（与 compare 对称），20 条截断写进 docstring 与 statistics.md；③check_selfconsistency 上 argparse（--help 正常、未知参数 rc=2，不再吞参数回 OK）；④报告模板「回归题」节改名「翻转题」与脚本输出同名对齐；⑤rubric-design kappa 段补成立条件与加题真实收益（均衡 n=25：26–28%/8%；偏斜 90%：约 35%/15%；n=40 仍 ~23%、≤10% 需 130+ 题——要么校到底要么承认 kappa 只配初筛、5% 复评才是真闸门），kappa 实现指向 _common 单一副本。
- **2.2.0（2026-09-21，七评）**：①flaky 清单与 compare 同一截断标准（>20 条列前 20、通过率最低在前、照报总数；标题保持与报告模板逐字一致）；②三脚本统一编码错误处理（非 UTF8 → stderr + rc=2）——此前裸 traceback rc=1 与各自 rc=1 语义撞号，且同类扫描发现不止新脚本一个；③自检脚本读文件容错（缺失/编码错误入问题清单不再崩溃），路径检查升级为「引用路径指向本库自有文件却不存在 → 报疑似旧名/搬家残留」——正是改名窗口真实存在过 16 分钟的 bug 形状；④CHANGELOG 数字改 fixture 无关写法；⑤rubric-design 如实写明 kappa 阈值抽样误差（MC 2 万次：n=25 时真 0.5 约 26–28% 过线、真 0.8 约 8% 被误拒），定位改为初筛 + 边界带追加标注 + 5% 复评兜底；⑥新增原则「修 bug 先扫同类」。本轮起每次修复附同类扫描与全量回归。
- **2.1.0（2026-09-21）**：①退出码契约补全——文件不存在/传目录不再裸 traceback（此前 Python 默认 rc=1，与"1=没有共同题"撞号，CI 分不清"路径写错"和"没有共同题"），stderr 明说 + rc=2；②翻转清单截断——超过 20 条只列前 20（回归在前）+ 总数，与 dup/跳号/改名告警同一截断标准（实测千题级输入可产出 500+ 条 bullet、占全文 96–98%）；③新增 scripts/check_selfconsistency.py——name=目录名、slug、内部绝对路径、外部软链四项机器自检（改名断链窗口三处同时暗断而无人能查的教训）；④输出流约定成文（stdout=报告全文可粘贴，stderr=致命错误）；⑤署名 DreamOfXM。
- **2.0.0（2026-09-21）**：更名 agent-evaluation → **skill-evaluation**，所有权归本地：真源目录从 OpenClaw workspace 迁至 `~/.agents/skills/`（与其余本地 skill 一致，OpenClaw 侧改为软链）；删除 .clawhub 安装记录、_meta 去除注册表 ownerId/publishedAt，版本分叉问题根除。description 明确评测对象含 agent skills 本身（消融 + 完备性检验）。
- **1.5.0（2026-09-21）**：新增「完备性检验（查漏）」（SKILL.md 第 2 节）——消融只能查冗余、查不了缺失，发版前用已知正确答案的真实案例撞判据，缺口当场补维度表，并注明边界（只覆盖已知答案的维度，未知的靠回流）；ablation.md 补边界注记（减法/加法配对），结尾补"被验证 ≠ 写全了"。
- **1.4.0（2026-09-21）**：输入 schema 严格校验（rc=2，stderr 报 文件:行号:原因；passed 必须布尔——字符串 'false' 是真值、此前会被判成通过；rep 必须整数；category/case_id 禁含 '|'）；结论行区分"总体显著"与"仅类目级显著"（后者注明总体数不显著、按多重比较残留对待）；flaky 节标题与 flaky_report.py 输出对齐；statistics.md 最小可检差异表补 80% 功效列（28/20/14/10pt）；ablation 案例补出处状态与"总账单未必降"限定；harness.md 补 `--flip-threshold` 参数名与 schema 说明。
- **1.3.x（2026-09-21）**：翻转阈值推荐值随 rep 自适应（1/n 向下取整，避免浮点边界：rep=3→0.33、rep=5→0.19）；"清单为空但 ≥2 题同向一步变化且零反向"漂移提示（含改善侧泄漏警告）；flaky_report rep=1 改 rc=0；类目改名告警与"疑似新增翻车"防误触；题数列改共同题口径；总体/类目检验只计共同题；多重比较校正（默认 BH，k 单类目不重复计）；kappa 同质批次守卫及 0.44→0.00 修正；(case_id, rep) 去重与 rep 跳号告警；新增 flaky_report.py 与 ablation.md。
- **1.0.0（2026-02）**：ClawHub 原版空壳（反模式/尖锐边界仅有标题与占位注释，无可执行实体），已被本地重写整体取代。
