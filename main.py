import os
import sys

# -------------------------------------------------
# Setup Python path
# -------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_DIR = os.path.join(BASE_DIR, "agent")

if AGENT_DIR not in sys.path:
    sys.path.insert(0, AGENT_DIR)

# -------------------------------------------------
# Imports
# -------------------------------------------------
try:
    from analyze import run_ruff
    from apply_patch import apply_patch
    from fixer import generate_patch
    from file_reader import read_file
    print("✅ All modules imported successfully\n")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# -------------------------------------------------
# Repository path
# -------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join("repos", "requests"))

# -------------------------------------------------
# Main
# -------------------------------------------------
def main():
    print("🤖 Automated Python Static Analysis Fixer")
    print("=" * 60)

    if not os.path.exists(REPO_ROOT):
        print(f"❌ Repository not found: {REPO_ROOT}")
        return

    print(f"📁 Target repository: {REPO_ROOT}")
    print("\n🔍 Running Ruff analysis...\n")

    issues = run_ruff(REPO_ROOT)
    f401_issues = [i for i in issues if i["code"] == "F401"]

    print(f"📊 Total issues found: {len(issues)}")
    print(f"📌 F401 (unused imports): {len(f401_issues)}\n")

    if not f401_issues:
        print("🎉 No F401 issues to fix.")
        return

    fixed = 0
    skipped = 0
    failed = 0

    for idx, issue in enumerate(f401_issues, 1):
        rel_path = issue["filename"]
        abs_path = os.path.join(REPO_ROOT, rel_path)
        message = issue["message"]

        print(f"[{idx}/{len(f401_issues)}] {rel_path}:{issue['line']}")
        print(f"➜ {message}")

        # -------------------------------------------------
        # SAFETY RULES
        # -------------------------------------------------

        # 1️⃣ Never touch __init__.py (public API)
        if os.path.basename(rel_path) == "__init__.py":
            print("⏭ Skipped (__init__.py public API)\n")
            skipped += 1
            continue

        # 2️⃣ Skip explicit re-export suggestions
        if "explicit re-export" in message:
            print("⏭ Skipped (library re-export)\n")
            skipped += 1
            continue

        # 3️⃣ File must exist
        if not os.path.exists(abs_path):
            print("⚠️ File not found\n")
            failed += 1
            continue

        code = read_file(abs_path)
        if not code:
            print("⚠️ Could not read file\n")
            failed += 1
            continue

        patch = generate_patch(abs_path, code, message)
        if not patch:
            print("⏭ No safe patch generated\n")
            skipped += 1
            continue

        success, error = apply_patch(REPO_ROOT, patch)

        if success:
            print("✅ Fixed\n")
            fixed += 1
        else:
            print(f"❌ Patch failed: {error}\n")
            failed += 1

    # -------------------------------------------------
    # Summary
    # -------------------------------------------------
    print("=" * 60)
    print("📈 SUMMARY")
    print("=" * 60)
    print(f"Fixed:   {fixed}")
    print(f"Skipped: {skipped}")
    print(f"Failed:  {failed}")

    print("\n🔁 Re-running Ruff...\n")
    remaining = run_ruff(REPO_ROOT)
    print(f"Remaining issues: {len(remaining)}")
    print("=" * 60)


# -------------------------------------------------
if __name__ == "__main__":
    main()
