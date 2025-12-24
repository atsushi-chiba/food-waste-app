import pytest
from app import app
from database import SessionLocal
from models import User

@pytest.fixture
def client():
    with app.test_client() as client:
        yield client

def login_client(client, username):
    return client.post('/login', data={'username': username}, follow_redirects=True)

def get_some_username():
    db = SessionLocal()
    try:
        user = db.query(User).first()
        return user.username if user else None
    finally:
        db.close()

def test_weekly_stats_returns_data(client):
    username = get_some_username()
    assert username is not None, "No user in DB to test with"

    # login
    resp = login_client(client, username)
    assert resp.status_code == 200

    # request weekly stats for a date known to have data
    resp = client.get('/api/weekly_stats?date=2025-12-17')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data is not None
    assert data.get('is_data_present') is True
    assert isinstance(data.get('dish_table'), list)
    assert len(data.get('dish_table')) > 0

def test_log_page_shows_table(client):
    username = get_some_username()
    assert username is not None, "No user in DB to test with"

    # login and fetch /log
    login_resp = login_client(client, username)
    assert login_resp.status_code == 200

    log_resp = client.get('/log')
    assert log_resp.status_code == 200
    html = log_resp.data.decode('utf-8')
    # the page should contain the data table container
    assert '<table id="dishTable"' in html
