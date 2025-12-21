import subprocess
import tempfile
import os

def apply_patch(repo_path, patch):
    """
    Apply patch with better error handling.
    """
    if not patch or not patch.strip():
        return False, "Empty patch"
    
    # Write patch to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False, encoding='utf-8') as f:
        f.write(patch)
        patch_file = f.name
    
    try:
        result = subprocess.run(
            ["git", "apply", "--check", patch_file],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode != 0:
            return False, f"Patch check failed: {result.stderr}"
        
        # Actually apply the patch
        result = subprocess.run(
            ["git", "apply", patch_file],
            cwd=repo_path,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            return True, None
        else:
            return False, result.stderr
    finally:
        if os.path.exists(patch_file):
            os.unlink(patch_file)