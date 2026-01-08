# GitHub Actions Setup Guide

## 🎯 What This Does

The GitHub Actions workflows automatically run AGI Engineer on your code:

1. **Automatic PR Checks** - Runs on every pull request, comments with issues found
2. **Manual Runs** - Run analysis or auto-fix on demand from GitHub UI

## 🚀 Setup Instructions

### Step 1: Add Groq API Key to GitHub Secrets

1. Get free Groq API key:
   - Visit: https://console.groq.com/keys
   - Sign up (free, no credit card)
   - Create API key

2. Add to GitHub repository:
   - Go to your repo on GitHub
   - Click **Settings** → **Secrets and variables** → **Actions**
   - Click **New repository secret**
   - Name: `GROQ_API_KEY`
   - Value: Your Groq API key (starts with `gsk_`)
   - Click **Add secret**

### Step 2: Enable Workflows

Workflows are in `.github/workflows/`:
- `code-quality.yml` - Auto-runs on PRs
- `manual-check.yml` - Manual trigger from Actions tab

They're automatically enabled when you push them to GitHub!

### Step 3: Test It

**Option A: Create a Test PR**
```bash
git checkout -b test-workflow
echo "# test" >> README.md
git add README.md
git commit -m "test: Trigger workflow"
git push origin test-workflow
```

Then create a PR on GitHub and watch the workflow run!

**Option B: Manual Run**
1. Go to **Actions** tab on GitHub
2. Click **Manual Code Quality Check**
3. Click **Run workflow**
4. Choose options and run

## 📊 What You'll See

### On Pull Requests:

The bot will comment with results:

```
🤖 AGI Engineer Analysis Results

Total Issues Found: 15

✅ Safe to Auto-Fix: 12 issues
⚠️  Needs Review: 3 issues

### Details
...detailed analysis...

---
Run locally: `python3 agi_engineer_v3.py . --smart --ai`
```

### On Manual Runs:

- See full analysis in Actions logs
- If "Apply fixes" enabled: Creates a PR with fixes
- Download analysis artifact for later review

## 🔧 Configuration

### Customize Workflows

Edit `.github/workflows/code-quality.yml`:

```yaml
# Run only on specific paths
paths:
  - '**.py'
  - 'src/**'

# Change Python version
python-version: '3.11'

# Add more steps
steps:
  - name: Custom step
    run: echo "Custom logic here"
```

### Disable AI (Use Only Ruff)

Remove `--ai` flag from workflow:

```yaml
run: |
  python agi_engineer_v3.py . --smart --analyze-only
  # Removed --ai flag
```

### Make Builds Fail on Issues

Change in `code-quality.yml`:

```yaml
- name: Check if issues found
  run: |
    TOTAL_ISSUES=${{ steps.extract.outputs.total_issues }}
    if [ "$TOTAL_ISSUES" != "0" ]; then
      echo "❌ Found $TOTAL_ISSUES issues"
      exit 1  # Change from exit 0 to exit 1
    fi
```

## 🎨 Features

### 1. Automatic PR Comments
- ✅ Shows issues found
- ✅ Categorizes by safety
- ✅ Updates existing comment (no spam)
- ✅ Includes AI suggestions

### 2. Manual Workflow
- ✅ Run on demand from GitHub UI
- ✅ Choose to analyze or apply fixes
- ✅ Enable/disable AI
- ✅ Auto-create PR with fixes

### 3. Artifacts
- ✅ Full analysis saved as artifact
- ✅ Download for 30 days
- ✅ Review offline

## 💡 Usage Examples

### Example 1: Pre-Merge Check

Every PR automatically gets checked:
1. Developer creates PR
2. Workflow runs in ~2 minutes
3. Bot comments with issues
4. Developer reviews and fixes
5. Merge when clean

### Example 2: Mass Cleanup

Use manual workflow with "Apply fixes":
1. Go to Actions → Manual Code Quality Check
2. Enable "Apply safe fixes"
3. Run workflow
4. Review the auto-generated PR
5. Merge to apply fixes

### Example 3: Scheduled Cleanup

Add to `code-quality.yml`:

```yaml
on:
  schedule:
    - cron: '0 0 * * 0'  # Every Sunday at midnight
```

## 🔒 Security

- API key stored securely in GitHub Secrets
- Workflow has minimal permissions
- Only reads code, writes comments
- No sensitive data exposed

## 🐛 Troubleshooting

### "API key not found"
**Solution:** Make sure `GROQ_API_KEY` is added to repository secrets

### "Workflow not running"
**Solution:** Check that workflows are enabled in Settings → Actions

### "Permission denied"
**Solution:** Check workflow has `pull-requests: write` permission

### "Analysis failed"
**Solution:** Check Actions logs for detailed error messages

## 📚 Next Steps

Once workflows are running:

1. **Monitor results** - Check PR comments
2. **Adjust thresholds** - Decide if builds should fail
3. **Enable auto-fix** - Let bot create fix PRs
4. **Schedule runs** - Add cron triggers
5. **Expand coverage** - Add to more repos

## 🎯 Best Practices

1. **Start with warnings** - Don't fail builds initially
2. **Review auto-fixes** - Always review generated PRs
3. **Use AI wisely** - May cost if using paid providers
4. **Keep secrets secure** - Never commit API keys
5. **Monitor costs** - Check Groq usage if needed

## 📖 More Info

- GitHub Actions Docs: https://docs.github.com/actions
- Workflow Syntax: https://docs.github.com/actions/reference/workflow-syntax-for-github-actions
- AGI Engineer Docs: See `V3_FEATURES.md` and `AI_FEATURES.md`

---

**Ready to go!** Push these workflows to GitHub and they'll start working automatically! 🚀
