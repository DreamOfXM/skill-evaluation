# 技能评估框架

<p align="center">
  <img src="https://img.shields.io/badge/Skill%20Score-4.8%2F5-brightgreen?style=for-the-badge" alt="技能评分">
  <img src="https://img.shields.io/badge/License-Apache%202.0-blue?style=for-the-badge" alt="许可证">
  <img src="https://img.shields.io/badge/Claude%20Code-兼容-green?style=for-the-badge" alt="Claude Code">
</p>

> 用于评估 Claude Code 技能质量的框架 — 它评什么，不评什么。

[English](README.md)

---

## 它评什么

本框架评估**技能写得怎么样**：

| 维度 | 检查内容 |
|------|---------|
| **触发准确性** | 是否在正确时机触发？ |
| **描述清晰度** | 用户3秒内能否理解功能？ |
| **结构完整性** | 是否包含所有必要章节？ |
| **指令可操作性** | 指令是否明确无歧义？ |

---

## 它不评什么

本框架**不评估**技能用起来效果：

| 不评估 | 原因 |
|--------|------|
| "这个技能实际用起来效果好不好？" | 需要用真实测试用例跑技能 |
| "这个技能在这个场景下合不合适？" | 需要根据使用场景判断 |
| "Agent 执行得对不对？" | 这是测试 Agent 能力，不是技能质量 |

**为什么这个区分很重要：**

Skill 写得好不好，最终看 agent 执行效果。但这两件事可能脱节：

- **写得好，用起来烂** → description 清楚、trigger 准确，但 agent 理解偏了或场景不匹配
- **写得烂，用起来行** → 全靠 agent 猜，换个场景就崩

Skill-evaluation 只管前半段：**它写得怎么样**。

---

## 四维度框架

| 维度 | 权重 | 测量内容 |
|------|------|---------|
| **触发准确性** | 25% | 是否在正确时机触发？ |
| **描述清晰度** | 25% | 用户能否理解它的功能？ |
| **结构完整性** | 25% | 是否包含所有必要章节？ |
| **指令可操作性** | 25% | 指令是否明确无歧义？ |

### 为什么要这四个维度？

1. **触发准确性** - 技能最容易在*入口*失败。太宽泛=频繁误触，太狭窄=永不触发。

2. **描述清晰度** - 用户3秒内根据描述决定是否使用技能。模糊=被放弃。

3. **结构完整性** - 边界清晰的技能（做什么+不做什么）用户满意度更高。

4. **指令可操作性** - 模糊指令（"考虑"、"在适当的时候"）导致LLM困惑。精确指令=可靠行为。

---

## 评测数据

评测了热门技能：

| 技能 | 评分 | 触发 | 描述 | 结构 | 可操作性 |
|------|------|------|------|------|---------|
| **技能评估框架** | **4.8** | 4.0 | 5.0 | 5.0 | 5.0 |
| brainstorming | 2.7 | 1.0 ⚠️ | 2.5 ⚠️ | 4.2 | 3.0 |
| hallmark | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| marketing-ideas | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| ui-ux-pro-max | 2.4 | 1.0 ⚠️ | 1.5 ⚠️ | 4.2 | 3.0 |
| project-skills | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 2.5 | 3.8 |

> **发现：** 大多数技能在触发准确性和描述清晰度上得分低于 3.0。常见问题：缺少 `_meta.json`、描述过长、缺少触发词优化。

---

## 快速开始

### 安装

```bash
# 克隆仓库
git clone https://github.com/DreamOfXM/skill-evaluation.git

# 添加为 Claude Code 技能
cp -r skill-evaluation ~/.agents/skills/
```

### 使用

```bash
# 评估任何技能
python3 ~/.agents/skills/skill-evaluation/scripts/evaluate_skill.py ~/.agents/skills/your-skill

# JSON 输出用于自动化
python3 ~/.agents/skills/skill-evaluation/scripts/evaluate_skill.py ~/.agents/skills/your-skill --output json
```

### Claude Code 集成

在任何 Claude Code 对话中：

```
帮我评测一下 brainstorming skill
```

---

## 评估报告示例

```markdown
# 技能质量报告：my-awesome-skill

**综合评分：3.8/5**

| 维度 | 分数 | 状态 |
|------|------|------|
| 触发准确性 | 4.0 | ✓ 良好 |
| 描述清晰度 | 3.5 | ⚠ 需改进 |
| 结构完整性 | 4.0 | ✓ 良好 |
| 指令可操作性 | 3.5 | ⚠ 需改进 |

## 发现的问题

### 高优先级（必须修复）
1. `_meta.json` 中缺少 `trigger_words`
2. 描述247字符（建议<100）

### 中优先级（建议修复）
1. 添加"何时不使用"章节
2. 澄清模糊短语"在适当的时候"
```

---

## 理论背景

### 问题

技能是给LLM的指令。与传统代码不同：
- **输出是非确定性的**
- **"正确"有多种定义**
- **测试需要判断而非断言**

### 方法

1. **多维度评分** - 单看一项说明不了问题
2. **锚点标准** - 每项分数有明确定义，不靠感觉
3. **指出具体问题** - 哪里不对，为什么不对，怎么改
4. **持续追踪** - 改完再测，看分数有没有涨

---

## 与其他方案对比

| 功能 | 技能评估框架 | 人工审查 |
|------|-------------|---------|
| 客观评分 | ✅ | ❌ |
| 触发分析 | ✅ | ⚠️ |
| 可操作性检查 | ✅ | ⚠️ |
| 改进建议 | ✅ | ✅ |

---

## 项目结构

```
skill-evaluation/
├── SKILL.md                          # 主入口
├── scripts/
│   ├── evaluate_skill.py             # 核心评估引擎
│   ├── test_triggers.py              # 触发词测试
│   ├── compare_runs.py               # 改进前后对比
│   └── flaky_report.py               # 差异检测
├── references/
│   ├── skill-rubric.md              # 评分标准
│   ├── trigger-testing.md            # 触发词分析方法
│   └── meta_template.md             # _meta.json模板
```

---

## 贡献

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 许可证

Apache License 2.0 - 详见 [LICENSE](LICENSE)。
