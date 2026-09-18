import json
import subprocess
import sys
import os
import shutil
import tempfile
from pathlib import Path
from datetime import datetime

class Harness:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.manifest_path = data_dir / "manifest.json"
        self.runs_dir = data_dir / "runs"
        self.results_dir = data_dir / "results"
        self.mutations_dir = data_dir / "mutations"
        self.cli_path = Path(__file__).resolve().parent / "harness_cli.py"

        self.runs_dir.mkdir(exist_ok=True)
        self.results_dir.mkdir(exist_ok=True)
        self.mutations_dir.mkdir(exist_ok=True)

    def run_command(self, cmd: list, cwd: str = None) -> tuple:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def _clone(self, repo_url: str, base_commit: str, target_dir: str):
        self.run_command(["git", "clone", repo_url, target_dir])
        self.run_command(["git", "checkout", base_commit], cwd=target_dir)

    def execute_case(self, case: dict):
        case_id = case["case_id"]
        repo_url = case["repository_url"]
        base_commit = case["base_commit"]

        case_run_dir = self.runs_dir / case_id
        case_run_dir.mkdir(exist_ok=True)

        clean_dir = case_run_dir / "clean"
        clean_dir.mkdir(exist_ok=True)

        mutated_dir = case_run_dir / "mutated"
        mutated_dir.mkdir(exist_ok=True)

        # We need a temp worktree
        with tempfile.TemporaryDirectory() as temp_repo:
            print(f"[{case_id}] Cloning to {temp_repo}...")
            self._clone(repo_url, base_commit, temp_repo)

            print(f"[{case_id}] Running clean control...")
            clean_out, clean_err = self._invoke_cli(temp_repo, base_commit, base_commit)
            self._save_run(clean_dir, clean_out, clean_err)

            print(f"[{case_id}] Applying mutation...")
            patch_file = self.mutations_dir / case_id / "mutation.patch"
            if patch_file.exists():
                code, out, err = self.run_command(["git", "apply", str(patch_file)], cwd=temp_repo)
                if code != 0:
                    print(f"[{case_id}] HARNESS_ERROR: Patch failed to apply. {err}")
                    return
            else:
                print(f"[{case_id}] HARNESS_ERROR: Missing patch file.")
                return

            mutated_commit = "MUTATED"

            print(f"[{case_id}] Running mutated control...")
            mut_out, mut_err = self._invoke_cli(temp_repo, base_commit, mutated_commit)
            self._save_run(mutated_dir, mut_out, mut_err)

    def _invoke_cli(self, repo_path: str, base_revision: str, target_revision: str):
        cmd = [
            sys.executable, str(self.cli_path),
            "--repo-path", repo_path,
            "--base-revision", base_revision,
            "--target-revision", target_revision
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout, result.stderr

    def _save_run(self, directory: Path, out: str, err: str):
        (directory / "stdout.txt").write_text(out)
        (directory / "stderr.txt").write_text(err)

        # Try parse json from stdout
        # Usually it's at the end or the whole thing
        try:
            # find last { and parse from there or just parse the whole thing
            parsed = json.loads(out)
            (directory / "response.json").write_text(json.dumps(parsed, indent=2))
        except json.JSONDecodeError:
            pass

def main():
    data_dir = Path(__file__).resolve().parent
    harness = Harness(data_dir)

    if not harness.manifest_path.exists():
        print("manifest.json not found.")
        sys.exit(1)

    with open(harness.manifest_path) as f:
        manifest = json.load(f)

    for case in manifest:
        harness.execute_case(case)

if __name__ == "__main__":
    main()
