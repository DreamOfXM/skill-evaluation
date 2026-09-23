# Contributing to Skill Evaluation

Thank you for your interest in contributing to Skill Evaluation! 🎉

## Code of Conduct

By participating, you are expected to uphold a welcoming, respectful community.

## How to Contribute

### Reporting Issues

Found a bug or have a suggestion? Please open an issue with:

1. **Clear title** describing the problem
2. **Steps to reproduce** (if bug)
3. **Expected vs actual behavior**
4. **Environment** (OS, agent framework + version, etc.)

### Pull Requests

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feat/your-feature`
3. **Make** your changes
4. **Test** your changes
5. **Commit** with clear messages (see below)
6. **Push** to your fork
7. **Open** a Pull Request

### Commit Message Format

```
<type>: <short description>

<longer description if needed>

Co-Authored-By: Your Name <email>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

### Adding New Evaluation Dimensions

1. Define rubric criteria in `references/skill-rubric.md`
2. Implement scorer in `scripts/evaluate_skill.py`
3. Add test cases
4. Update documentation
5. Ensure self-evaluation score ≥ 4.5

### Style Guide

- Python: Follow PEP 8
- Markdown: Use clear headers, bullet points
- Comments: Explain *why*, not *what*

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/skill-evaluation.git

# No dependencies required (Python 3 stdlib only)

# Self-evaluate
python3 scripts/evaluate_skill.py .

# Consistency self-check
python3 scripts/check_selfconsistency.py
```

## Recognition

Contributors will be:
- Added to README.md Contributors section
- Mentioned in release notes
- Given credit in code comments

## Questions?

- Open a Discussion
- Check existing issues
- Email maintainer

---

**Remember:** Every contribution, no matter how small, helps the community!
