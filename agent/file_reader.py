import os

def read_file(file_path):
    """Reads file from an absolute path"""
    if not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()