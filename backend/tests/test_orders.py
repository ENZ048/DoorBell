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
