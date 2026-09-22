# Skill Evaluation

<p align="center">
  <img src="https://img.shields.io/badge/Skill%20Score-4.8%2F5-brightgreen?style=for-the-badge" alt="Skill Score">
  <img src="https://img.shields.io/badge/License-Apache%202.0-blue?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/Claude%20Code-Compatible-green?style=for-the-badge" alt="Claude Code">
</p>

> A framework for evaluating Claude Code skill quality — what it does and doesn't evaluate.

[Read in Chinese](README_zh.md)

---

## What It Evaluates

This framework evaluates **how well a skill is written**:

| Dimension | What It Checks |
|-----------|---------------|
| **Trigger Accuracy** | Does it fire at the right time? |
| **Description Clarity** | Can users understand what it does in 3 seconds? |
| **Structure Completeness** | Does it have all necessary sections? |
| **Actionability** | Are instructions unambiguous? |

---

## What It Doesn't Evaluate

This framework does NOT evaluate **how well a skill works**:

| Not Evaluated | Reason |
|---------------|-------|
| "Does the skill work well in practice?" | This requires running the skill with real test cases |
| "Is this skill appropriate for this scenario?" | This is a judgment call based on use case |
| "Does the agent execute correctly?" | This tests the agent's capability, not the skill's quality |

**Why this distinction matters:**

A well-written skill doesn't guarantee good execution. These can diverge:

- **Well-written, bad results** → Clear description, good triggers, but agent misinterprets or wrong scenario
- **Poorly written, works anyway** → Relies on agent guessing, breaks in different scenarios

Skill-evaluation only covers the first half: **is it well-written?**

---

## The 4-Dimension Framework

| Dimension | Weight | What It Measures |
|-----------|--------|-----------------|
| **Trigger Accuracy** | 25% | Does it fire at the right time? |
| **Description Clarity** | 25% | Can users understand what it does? |
| **Structure Completeness** | 25% | Does it have all necessary sections? |
| **Actionability** | 25% | Are instructions unambiguous? |

### Why These Dimensions?

1. **Trigger Accuracy** - Skills fail most often at the *entry point*. Too broad = misfires. Too narrow = never activates.

2. **Description Clarity** - Users decide in 3 seconds based on description. Vague = abandoned.

3. **Structure Completeness** - Skills with clear boundaries (what it does + doesn't do) have higher user satisfaction.

4. **Actionability** - Vague instructions ("consider", "when appropriate") cause LLM confusion. Precise instructions = reliable behavior.

---

## Benchmark Results

Evaluated popular skills:

| Skill | Score | Trigger | Description | Structure | Actionability |
|-------|-------|---------|-------------|-----------|---------------|
| **skill-evaluation** | **4.8** | 4.0 | 5.0 | 5.0 | 5.0 |
| brainstorming | 2.7 | 1.0 ⚠️ | 2.5 ⚠️ | 4.2 | 3.0 |
| hallmark | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| marketing-ideas | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 3.3 | 3.0 |
| ui-ux-pro-max | 2.4 | 1.0 ⚠️ | 1.5 ⚠️ | 4.2 | 3.0 |
| project-skills | 2.2 | 1.0 ⚠️ | 1.5 ⚠️ | 2.5 | 3.8 |

> **Finding:** Most evaluated skills scored below 3.0 on trigger accuracy and description clarity. Common issues: missing `_meta.json`, overly long descriptions, no trigger word optimization.

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/DreamOfXM/skill-evaluation.git

# Add as a Claude Code skill
cp -r skill-evaluation ~/.agents/skills/
```

### Usage

```bash
# Evaluate any skill
python3 ~/.agents/skills/skill-evaluation/scripts/evaluate_skill.py ~/.agents/skills/your-skill

# JSON output for automation
python3 ~/.agents/skills/skill-evaluation/scripts/evaluate_skill.py ~/.agents/skills/your-skill --output json
```

### Claude Code Integration

In any Claude Code conversation:

```
帮我评测一下 brainstorming skill
```

---

## Evaluation Report Example

```markdown
# Skill Quality Report: my-awesome-skill

**Overall Score: 3.8/5**

| Dimension | Score | Status |
|-----------|-------|--------|
| Trigger Accuracy | 4.0 | ✓ Good |
| Description Clarity | 3.5 | ⚠ Needs Work |
| Structure Completeness | 4.0 | ✓ Good |
| Actionability | 3.5 | ⚠ Needs Work |

## Issues Found

### High Priority (Must Fix)
1. Missing `trigger_words` in `_meta.json`
2. Description is 247 characters (recommend <100)

### Medium Priority (Recommended)
1. Add "When NOT to Use" section
2. Clarify vague phrase "when appropriate"
```

---

## Theory

### The Problem

Skills are instructions for LLMs. Unlike traditional code:
- **Output is non-deterministic**
- **"Correct" has multiple definitions**
- **Testing requires judgment, not assertions**

### Approach

1. **Multi-dimensional scoring** - No single metric captures quality
2. **Anchor-based rubrics** - Scores have specific, measurable criteria
3. **Actionable feedback** - Problems point to solutions
4. **Iterative improvement** - Track progress over time

---

## Comparison

| Feature | Skill Evaluation | Manual Review |
|---------|------------------|---------------|
| Objective scoring | ✅ | ❌ |
| Trigger analysis | ✅ | ⚠️ |
| Actionability check | ✅ | ⚠️ |
| Improvement suggestions | ✅ | ✅ |

---

## Architecture

```
skill-evaluation/
├── SKILL.md                          # Main entry point
├── scripts/
│   ├── evaluate_skill.py             # Core evaluation engine
│   ├── test_triggers.py              # Trigger word testing
│   ├── compare_runs.py              # Before/after comparison
│   └── flaky_report.py               # Variance detection
├── references/
│   ├── skill-rubric.md              # Scoring criteria
│   ├── trigger-testing.md            # Trigger analysis method
│   └── meta_template.md             # _meta.json template
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

Apache License 2.0 - see [LICENSE](LICENSE).
