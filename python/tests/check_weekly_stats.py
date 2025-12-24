import sys
import os
import json
import logging

logger = logging.getLogger(__name__)

try:
    pass
except Exception as e:
    logger.error("requests is not installed: %s", e)
    sys.exit(1)


def main():
    # ensure project root (python/) is on sys.path for imports when running as a script
    basedir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(basedir)  # one level up (python/)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # imports that depend on project_root being in sys.path
    from database import SessionLocal
    from models import User
    from app import app

    try:
        pass
    except Exception as e:
        logger.error("requests is not installed: %s", e)
        sys.exit(1)

    # get a username from DB
    db = SessionLocal()
    try:
        user = db.query(User).first()
        if not user:
            print("No user found in DB")
            sys.exit(1)
        username = user.username
        logger.info("Using username: %s", username)
    finally:
        db.close()

    with app.test_client() as client:
        login_resp = client.post(
            "/login", data={"username": username}, follow_redirects=True
        )
        logger.info("POST /login status: %s", login_resp.status_code)

        # GET /log (should be HTML)
        log_resp = client.get("/log")
        logger.info("/log status: %s", log_resp.status_code)
        logger.debug("/log content snippet: %s", log_resp.data.decode("utf-8")[:200])

        # GET API weekly stats for a sample date
        stats_resp = client.get("/api/weekly_stats?date=2025-12-17")
        logger.info("/api/weekly_stats status: %s", stats_resp.status_code)
        try:
            logger.info(
                "\n%s", json.dumps(stats_resp.get_json(), ensure_ascii=False, indent=2)
            )
        except Exception as e:
            logger.error("Failed to parse JSON: %s", e)
            logger.debug("Response text: %s", stats_resp.data.decode("utf-8"))

        # Also check that is_data_present is True
        try:
            data = stats_resp.get_json()
            print("is_data_present:", data.get("is_data_present"))
            print("dish_table length:", len(data.get("dish_table", [])))
        except Exception:
            pass


if __name__ == "__main__":
    main()
