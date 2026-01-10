import pytest
from database import SessionLocal
from models import User
import python.services as services
import uuid


@pytest.fixture
def db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_user(db, username="test_user"):
    unique = f"{username}_{uuid.uuid4().hex[:8]}"
    u = User(username=unique, password="x", email=f"{unique}@example.com")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def remove_user(db, user_id):
    u = db.query(User).get(user_id)
    if u:
        db.delete(u)
        db.commit()


def test_no_reduction_returns_zero(db, monkeypatch):
    user = create_user(db, "p_test1")

    # Simulate last_week=100, this_week=100, baseline irrelevant
    monkeypatch.setattr(services, "get_last_two_weeks", lambda _db, uid: (100.0, 100.0))
    monkeypatch.setattr(
        services, "get_total_grams_for_weeks", lambda _db, uid, weeks_ago=4: 400.0
    )

    result = services.calculate_weekly_points_logic(db, user.id)

    assert result["points_added"] == 0
    refreshed = db.query(User).get(user.id)
    assert refreshed.total_points == 0

    remove_user(db, user.id)


def test_25_percent_reduction_gives_2_points(db, monkeypatch):
    user = create_user(db, "p_test2")

    # last_week=100, this_week=75 => 25% reduction => 2 points
    monkeypatch.setattr(services, "get_last_two_weeks", lambda _db, uid: (100.0, 75.0))
    monkeypatch.setattr(
        services, "get_total_grams_for_weeks", lambda _db, uid, weeks_ago=4: 400.0
    )

    result = services.calculate_weekly_points_logic(db, user.id)

    assert result["points_added"] == 2
    refreshed = db.query(User).get(user.id)
    assert refreshed.total_points == 2

    remove_user(db, user.id)


def test_baseline_limits_the_rate(db, monkeypatch):
    user = create_user(db, "p_test3")

    # last_week small reduction (20%), but baseline indicates larger possible (60%)
    monkeypatch.setattr(services, "get_last_two_weeks", lambda _db, uid: (100.0, 80.0))
    # past_4_weeks_total=800 -> baseline=200 -> rate_baseline = (200-80)/200 = 0.6
    monkeypatch.setattr(
        services, "get_total_grams_for_weeks", lambda _db, uid, weeks_ago=4: 800.0
    )

    result = services.calculate_weekly_points_logic(db, user.id)

    # final_rate = min(0.2, 0.6) = 0.2 => 20% => 2 points
    assert result["points_added"] == 2
    refreshed = db.query(User).get(user.id)
    assert refreshed.total_points == 2

    remove_user(db, user.id)


def test_baseline_and_last_week_zero_and_this_week_zero(db, monkeypatch):
    user = create_user(db, "p_test4")

    # both last_week and baseline are zero, this_week is zero -> no points
    monkeypatch.setattr(services, "get_last_two_weeks", lambda _db, uid: (0.0, 0.0))
    monkeypatch.setattr(
        services, "get_total_grams_for_weeks", lambda _db, uid, weeks_ago=4: 0.0
    )

    result = services.calculate_weekly_points_logic(db, user.id)

    assert result["points_added"] == 0
    refreshed = db.query(User).get(user.id)
    assert refreshed.total_points == 0
    assert refreshed.last_points_awarded_week_start is not None

    remove_user(db, user.id)


def test_onboarding_awarded_for_first_week(db, monkeypatch):
    user = create_user(db, "p_onboard")

    # first week: last_week=0, baseline=0, but this_week >= MIN_RECORD_WEIGHT
    monkeypatch.setattr(services, "get_last_two_weeks", lambda _db, uid: (0.0, 120.0))
    monkeypatch.setattr(
        services, "get_total_grams_for_weeks", lambda _db, uid, weeks_ago=4: 0.0
    )

    result = services.calculate_weekly_points_logic(db, user.id)

    assert result["points_added"] == services.ONBOARDING_POINTS
    refreshed = db.query(User).get(user.id)
    assert refreshed.total_points == services.ONBOARDING_POINTS
    assert refreshed.last_points_awarded_week_start is not None

    # second run: should be idempotent
    result2 = services.calculate_weekly_points_logic(db, user.id)
    assert result2["points_added"] == 0
    assert result2.get("message") == "already_awarded"

    remove_user(db, user.id)


def test_minimum_reduction_threshold(db, monkeypatch):
    # Case A: 4% reduction -> no points
    user_a = create_user(db, "p_threshold_a")

    monkeypatch.setattr(services, "get_last_two_weeks", lambda _db, uid: (100.0, 96.0))
    monkeypatch.setattr(
        services, "get_total_grams_for_weeks", lambda _db, uid, weeks_ago=4: 500.0
    )

    result = services.calculate_weekly_points_logic(db, user_a.id)
    assert result["points_added"] == 0
    refreshed = db.query(User).get(user_a.id)
    assert refreshed.total_points == 0

    remove_user(db, user_a.id)

    # Case B: 5% reduction -> should award points
    user_b = create_user(db, "p_threshold_b")
    monkeypatch.setattr(services, "get_last_two_weeks", lambda _db, uid: (100.0, 95.0))
    monkeypatch.setattr(
        services, "get_total_grams_for_weeks", lambda _db, uid, weeks_ago=4: 500.0
    )

    result2 = services.calculate_weekly_points_logic(db, user_b.id)
    assert result2["points_added"] > 0

    remove_user(db, user_b.id)


def test_increase_results_in_no_points(db, monkeypatch):
    user = create_user(db, "p_test5")

    # last_week=100, this_week=150 => increase => negative reduction => no points
    monkeypatch.setattr(services, "get_last_two_weeks", lambda _db, uid: (100.0, 150.0))
    monkeypatch.setattr(
        services, "get_total_grams_for_weeks", lambda _db, uid, weeks_ago=4: 400.0
    )

    result = services.calculate_weekly_points_logic(db, user.id)

    assert result["points_added"] == 0
    refreshed = db.query(User).get(user.id)
    assert refreshed.total_points == 0
    assert refreshed.last_points_awarded_week_start is not None

    # 二回目実行しても付与されない（idempotency）
    result2 = services.calculate_weekly_points_logic(db, user.id)
    assert result2["points_added"] == 0
    assert result2.get("message") == "already_awarded"

    remove_user(db, user.id)
