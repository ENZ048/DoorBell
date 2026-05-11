async def test_upload_inserts_valid_rows(client):
    csv_body = (
        "order_id,customer_name,customer_phone,product,delivery_slot_label,address,pincode,payment_type,amount\n"
        "SNT-1,Ananya,+919876543210,Tee,kal subah,addr,560038,COD,1499\n"
        "SNT-2,Rohit,9876543211,Tee,kal,addr,560001,PREPAID,999\n"
    ).encode("utf-8")
    response = await client.post(
        "/api/orders/upload",
        files={"file": ("orders.csv", csv_body, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_parsed"] == 2
    assert len(data["inserted"]) == 2
    assert data["rejected"] == []
    assert data["inserted"][0]["order_id"] == "SNT-1"


async def test_upload_reports_rejected_rows(client):
    csv_body = (
        "order_id,customer_name,customer_phone,product,delivery_slot_label,address,pincode,payment_type,amount\n"
        "SNT-3,X,bad,P,kal,addr,560001,COD,100\n"
        "SNT-4,Y,+919876543212,P,kal,addr,560001,PREPAID,500\n"
    ).encode("utf-8")
    response = await client.post(
        "/api/orders/upload",
        files={"file": ("orders.csv", csv_body, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_parsed"] == 2
    assert len(data["inserted"]) == 1
    assert len(data["rejected"]) == 1
    assert data["rejected"][0]["row_number"] == 2


async def test_upload_missing_required_column_returns_422(client):
    csv_body = b"order_id,customer_name\nSNT-5,A"
    response = await client.post(
        "/api/orders/upload",
        files={"file": ("bad.csv", csv_body, "text/csv")},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "INVALID_CSV"


async def test_upload_persists_to_mongo(client, mock_db):
    csv_body = (
        "order_id,customer_name,customer_phone,product,delivery_slot_label,address,pincode,payment_type,amount\n"
        "SNT-6,Z,+919876543213,P,kal,addr,560001,COD,777\n"
    ).encode("utf-8")
    await client.post("/api/orders/upload", files={"file": ("o.csv", csv_body, "text/csv")})
    docs = await mock_db["orders"].find().to_list(length=10)
    assert len(docs) == 1
    assert docs[0]["order_id"] == "SNT-6"
    assert docs[0]["call_status"] == "pending"


async def test_list_orders_returns_all(client, mock_db):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    await mock_db["orders"].insert_many([
        {"order_id": "A", "call_status": "pending", "created_at": now,
         "customer_name": "x", "customer_phone": "+919999999999",
         "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
         "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
         "transcript": [], "extracted_variables": {}, "actions": [],
         "updated_at": now, "bucket": None, "action_state": None,
         "bolna_call_id": None, "recording_url": None, "updated_address": None,
         "reschedule_preference": None},
        {"order_id": "B", "call_status": "completed", "bucket": "confirmed",
         "created_at": now, "customer_name": "x", "customer_phone": "+919999999998",
         "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
         "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
         "transcript": [], "extracted_variables": {}, "actions": [],
         "updated_at": now, "action_state": None,
         "bolna_call_id": None, "recording_url": None, "updated_address": None,
         "reschedule_preference": None},
    ])
    resp = await client.get("/api/orders")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["orders"]) == 2


async def test_list_orders_filters_by_bucket(client, mock_db):
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    base = {"customer_name": "x", "customer_phone": "+919999999999",
            "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
            "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
            "transcript": [], "extracted_variables": {}, "actions": [],
            "updated_at": now, "action_state": None,
            "bolna_call_id": None, "recording_url": None, "updated_address": None,
            "reschedule_preference": None, "created_at": now}
    await mock_db["orders"].insert_many([
        {**base, "order_id": "A", "call_status": "completed", "bucket": "confirmed"},
        {**base, "order_id": "B", "call_status": "completed", "bucket": "escalate"},
    ])
    resp = await client.get("/api/orders?bucket=confirmed")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["orders"]) == 1
    assert body["orders"][0]["order_id"] == "A"


async def test_get_order_by_id_includes_events(client, mock_db):
    from datetime import datetime, timezone
    from bson import ObjectId
    now = datetime.now(timezone.utc)
    oid = ObjectId()
    await mock_db["orders"].insert_one({
        "_id": oid, "order_id": "X", "call_status": "pending",
        "customer_name": "x", "customer_phone": "+919999999999",
        "product": "p", "delivery_slot": "s", "delivery_slot_label": "kal",
        "address": "a", "pincode": "560001", "payment_type": "COD", "amount": 1,
        "transcript": [], "extracted_variables": {}, "actions": [],
        "created_at": now, "updated_at": now, "bucket": None, "action_state": None,
        "bolna_call_id": None, "recording_url": None, "updated_address": None,
        "reschedule_preference": None,
    })
    await mock_db["call_events"].insert_one({
        "order_id": oid, "type": "created", "source": "csv", "payload": {}, "ts": now,
    })
    resp = await client.get(f"/api/orders/{oid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["order_id"] == "X"
    assert len(body["events"]) == 1


async def test_get_unknown_order_returns_404(client):
    from bson import ObjectId
    resp = await client.get(f"/api/orders/{ObjectId()}")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ORDER_NOT_FOUND"
