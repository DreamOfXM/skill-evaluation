# Deploy to GitHub

## Prerequisites

1. GitHub CLI (`gh`) installed and authenticated
2. Git configured
3. SSH key added to GitHub (optional)

## Quick Deploy

```bash
# Navigate to skill directory
cd ~/.agents/skills/skill-evaluation

# Initialize git if needed
git init

# Add all files
git add .

# Commit
git commit -m "feat: initial release of skill-evaluation

- First scientific framework for Claude Code skill quality
- 4-dimension evaluation (trigger, description, structure, actionability)
- Real benchmark data from popular skills
- Apache 2.0 License

Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>"

# Create GitHub repo (if not exists)
gh repo create skill-evaluation --public --source=. --push

# Or if repo already exists
git remote add origin https://github.com/DreamOfXM/skill-evaluation.git
git branch -M main
git push -u origin main
```

## Manual Deploy (Web UI)

1. Go to https://github.com/new
2. Repository name: `skill-evaluation`
3. Description: `The first scientific framework for evaluating Claude Code skill quality.`
4. Public
5. License: Apache License 2.0
6. Click "Create repository"
7. Follow instructions to push existing code

## Post-Deploy Steps

1. Add topics to repo:
   - `claude-code`
   - `claude-code-skill`
   - `ai-agents`
   - `evaluation`
   - `developer-tools`

2. Enable GitHub Pages (optional):
   - Settings → Pages → Source: main branch

3. Add to README badge links:
   - Stars count
   - License badge

## Verification

After deploy, check:
- [ ] README renders correctly
- [ ] License file visible
- [ ] SKILL.md accessible
- [ ] Scripts executable

## Updating

```bash
git add .
git commit -m "feat: describe changes"
git push
```
