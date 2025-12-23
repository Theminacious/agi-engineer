#!/usr/bin/env python3
"""
Test script to create a sample repo with MANY code issues for AGI Engineer to fix
"""
import os
import shutil
from git import Repo

# Create test repo
test_repo_path = "repos/test-repo"

if os.path.exists(test_repo_path):
    shutil.rmtree(test_repo_path)

os.makedirs(test_repo_path)

# Initialize git repo
repo = Repo.init(test_repo_path)

# Create files with LOTS of issues
files = {
    "main.py": '''import os
import sys
import json
import math
import random
import datetime

def greet(name):
    message = f"Hello"
    value = f"42"
    return message

def calculate(x):
    result = x + 1
    if result is None:
        pass
    return result

class Person:
    def __init__(self):
        self.name = f"John"
        self.age = f"30"
    
    def info(self):
        return f"Person"

if __name__ == "__main__":
    print(greet("World"))
    
''',
    
    "utils.py": '''import math
import datetime
import subprocess
import collections
import itertools

def calculate():
    result = f"42"
    unused_var = 123
    return result
    
def format_date():
    return f"today"

def process_data(data):
    if data is None:
        return None
    return data

def helper_func():   
    x = f"test"
    y = f"data"
    z = f"value"
    return x
''',

    "config.py": '''import os
import sys
import json
import re

CONFIG = {
    "debug": f"true",
    "mode": f"prod",
    "timeout": f"30"
}

def get_config(key):
    if key is None:
        return None
    return CONFIG.get(key)

def validate_config():
    temp_var = "unused"
    return True
''',

    "database.py": '''import sqlite3
import psycopg2
import mysql.connector

class Database:
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect(self):
        self.conn = None
        if self.conn is None:
            pass
        return f"connected"
    
    def query(self, sql):
        unused_module = sqlite3
        result = f"result"
        return result
    
    def close(self):    
        if self.conn:
            self.conn.close()
''',

    "api.py": '''import requests
import httpx
import urllib3

def fetch_data(url):
    unused = "variable"
    if url is None:
        return None
    response = f"data"
    return response

def post_data(url, data):
    unused_var1 = 1
    unused_var2 = 2
    result = f"success"
    return result
''',

    "handlers.py": '''import json
import logging
import traceback

class Handler:
    def handle(self, event):   
        if event is None:
            return None
        unused = f"temp"
        status = f"ok"
        return status
    
    def process(self, item):
        name = f"item"
        value = f"123"
        debug = f"false"
        return name
''',

    "validators.py": '''import re
import typing
import abc

def validate_email(email):
    unused_pattern = "pattern"
    if email is None:
        return None
    result = f"valid"
    return result

def validate_phone(phone):  
    if phone is None:
        return None
    unused_lib = typing
    return f"ok"

def validate_url(url):
    unused_abc = abc
    return f"url_ok"
''',

    "models.py": '''import dataclasses
import enum
import types
import copy

class User:
    def __init__(self, name, email):   
        self.name = f"name"
        self.email = f"email"
        self.unused = "value"
    
    def to_dict(self):
        if self is None:
            return None
        return {
            "name": f"user",
            "email": f"test@example.com"
        }

class Product:
    def __init__(self, title, price):
        self.title = f"product"
        self.price = f"99.99"
        unused_copy = copy
        unused_enum = enum
    
    def info(self):
        unused_types = types
        return f"info"
'''
}

for filename, content in files.items():
    filepath = os.path.join(test_repo_path, filename)
    with open(filepath, 'w') as f:
        f.write(content)

# Commit
repo.index.add(list(files.keys()))
repo.index.commit("Initial commit with many issues")

print(f"✅ Created comprehensive test repository at: {test_repo_path}")
print(f"📊 Created {len(files)} files with errors")
print("\nRun: python3 agi_engineer_v2.py repos/test-repo")
