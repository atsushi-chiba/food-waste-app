from app import app
from database import SessionLocal
from models import User


def test_redeem_success_and_failure():
    with app.test_client() as client:
        db = SessionLocal()
        try:
            # create a unique user
            u = User(
                username="redeemtest",
                password="x",
                email="redeemtest@example.com",
                total_points=600,
            )
            db.add(u)
            db.commit()
            db.refresh(u)

            # login by setting session user_id using test_client
            with client.session_transaction() as sess:
                sess["user_id"] = u.id

            # Attempt redeem item costing 500 -> should succeed
            resp = client.post(
                "/api/redeem", json={"item_name": "エコバッグ", "cost": 500}
            )
            assert resp.status_code == 200
            data = resp.get_json()
            assert "remaining_points" in data
            assert data["remaining_points"] == 100

            # Attempt redeem item costing 200 -> should fail due to insufficient points (only 100 left)
            resp2 = client.post(
                "/api/redeem", json={"item_name": "リサイクルボックス", "cost": 200}
            )
            assert resp2.status_code == 403
            data2 = resp2.get_json()
            assert data2["message"] == "ポイントが不足しています。"

        finally:
            # cleanup
            db.delete(db.get(User, u.id))
            db.commit()
            db.close()
