import json
import sys
import os
# ensure project root (python/) is on sys.path for imports when running as a script
basedir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(basedir)  # one level up (python/)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from database import SessionLocal
from models import User

try:
    import requests
except Exception as e:
    print('requests is not installed:', e)
    sys.exit(1)

# get a username from DB
db = SessionLocal()
try:
    user = db.query(User).first()
    if not user:
        print('No user found in DB')
        sys.exit(1)
    username = user.username
    print('Using username:', username)
finally:
    db.close()

from app import app

with app.test_client() as client:
    login_resp = client.post('/login', data={'username': username}, follow_redirects=True)
    print('POST /login status:', login_resp.status_code)

    # GET /log (should be HTML)
    log_resp = client.get('/log')
    print('/log status:', log_resp.status_code)
    print('/log content snippet:', log_resp.data.decode('utf-8')[:200])

    # GET API weekly stats for a sample date
    stats_resp = client.get('/api/weekly_stats?date=2025-12-17')
    print('/api/weekly_stats status:', stats_resp.status_code)
    try:
        print(json.dumps(stats_resp.get_json(), ensure_ascii=False, indent=2))
    except Exception as e:
        print('Failed to parse JSON:', e)
        print('Response text:', stats_resp.data.decode('utf-8'))

    # Also check that is_data_present is True
    try:
        data = stats_resp.get_json()
        print('is_data_present:', data.get('is_data_present'))
        print('dish_table length:', len(data.get('dish_table', [])))
    except Exception:
        pass
