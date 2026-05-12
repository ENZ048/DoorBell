
import pytest

from app.csv_parser import ParseResult, parse_csv


def _csv(rows: list[str]) -> bytes:
    header = "order_id,customer_name,customer_phone,product,delivery_slot_label,address,pincode,payment_type,amount"
    return ("\n".join([header, *rows])).encode("utf-8")


def test_happy_path_single_row():
    body = _csv([
        "SNT-1,Ananya Sharma,+919876543210,Snitch Tee,kal subah 10-1,B-204 BLR,560038,COD,1499"
    ])
    result: ParseResult = parse_csv(body)
    assert result.total_parsed == 1
    assert len(result.inserted) == 1
    assert result.rejected == []
    o = result.inserted[0]
    assert o.order_id == "SNT-1"
    assert o.customer_phone == "+919876543210"
    assert o.amount == 1499
    assert o.payment_type.value == "COD"


def test_normalizes_indian_phone_without_plus():
    body = _csv([
        "SNT-2,Rohit,9876543210,Tee,kal,addr,560001,PREPAID,999"
    ])
    result = parse_csv(body)
    assert len(result.inserted) == 1
    assert result.inserted[0].customer_phone == "+919876543210"


def test_normalizes_10_digit_with_91_prefix():
    body = _csv([
        "SNT-3,Priya,91 9876543210,Tee,kal,addr,560001,PREPAID,999"
    ])
    result = parse_csv(body)
    assert result.inserted[0].customer_phone == "+919876543210"


def test_rejects_invalid_phone():
    body = _csv([
        "SNT-4,X,12345,Tee,kal,addr,560001,COD,100"
    ])
    result = parse_csv(body)
    assert result.inserted == []
    assert len(result.rejected) == 1
    assert "phone" in result.rejected[0].reason.lower()
    assert result.rejected[0].row_number == 2  # header is row 1


def test_rejects_invalid_amount():
    body = _csv([
        "SNT-5,X,+919876543210,Tee,kal,addr,560001,COD,not_a_number"
    ])
    result = parse_csv(body)
    assert result.inserted == []
    assert len(result.rejected) == 1
    assert "amount" in result.rejected[0].reason.lower()


def test_rejects_unknown_payment_type():
    body = _csv([
        "SNT-6,X,+919876543210,Tee,kal,addr,560001,UPI,100"
    ])
    result = parse_csv(body)
    assert result.inserted == []
    assert "payment_type" in result.rejected[0].reason.lower()


def test_case_insensitive_headers():
    header = "Order_ID,Customer_Name,Customer_Phone,Product,Delivery_Slot_Label,Address,Pincode,Payment_Type,Amount"
    body = (header + "\nSNT-7,A,+919876543210,P,kal,addr,560001,COD,500").encode("utf-8")
    result = parse_csv(body)
    assert len(result.inserted) == 1


def test_missing_required_column():
    body = b"order_id,customer_name\nSNT-8,X"
    with pytest.raises(ValueError, match="missing columns"):
        parse_csv(body)


def test_handles_bom():
    csv_text = "﻿order_id,customer_name,customer_phone,product,delivery_slot_label,address,pincode,payment_type,amount\nSNT-9,A,+919876543210,P,kal,addr,560001,COD,500"
    result = parse_csv(csv_text.encode("utf-8"))
    assert len(result.inserted) == 1


def test_partial_success_mixed_rows():
    body = _csv([
        "SNT-10,A,+919876543210,P,kal,addr,560001,COD,500",
        "SNT-11,B,bad,P,kal,addr,560001,COD,500",
        "SNT-12,C,+919876543211,P,kal,addr,560001,PREPAID,800",
    ])
    result = parse_csv(body)
    assert result.total_parsed == 3
    assert len(result.inserted) == 2
    assert len(result.rejected) == 1
    assert result.rejected[0].row_number == 3
