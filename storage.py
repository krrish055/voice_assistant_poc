import json
import os
from datetime import datetime

DB_FILE = "db.json"

def save_to_db(entry: dict):
    data = _read()
    entry["timestamp"] = datetime.utcnow().isoformat()
    data.append(entry)
    _write(data)

def get_all_data() -> list:
    return _read()

def _read() -> list:
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def _write(data: list):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)
