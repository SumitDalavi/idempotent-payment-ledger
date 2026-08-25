import pytest
from fastapi.testclient import TestClient
from main import app, SessionLocal

client = TestClient(app)

def test_successful_transfer(mocker):
    mock_db = mocker.MagicMock()
    mock_db.execute.return_value.fetchone.return_value = None
    mock_db.execute.return_value.scalar.return_value = 100 # Positive balance
    
    mocker.patch("main.SessionLocal", return_value=mock_db)
    
    response = client.post(
        "/transfer",
        params={"from_acct": "A", "to_acct": "B", "amount": 50.0},
        headers={"idempotency-key": "key123"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_db.commit.assert_called_once()

def test_idempotent_transfer(mocker):
    mock_db = mocker.MagicMock()
    # Simulate already exists
    mock_db.execute.return_value.fetchone.return_value = ["{'status': 'success', 'transferred': 50.0}"]
    
    mocker.patch("main.SessionLocal", return_value=mock_db)
    
    response = client.post(
        "/transfer",
        params={"from_acct": "A", "to_acct": "B", "amount": 50.0},
        headers={"idempotency-key": "key123"}
    )
    
    assert response.status_code == 200
    assert "success" in response.text
    # Should not commit a second time
    mock_db.commit.assert_not_called()

def test_insufficient_funds(mocker):
    mock_db = mocker.MagicMock()
    mock_db.execute.return_value.fetchone.return_value = None
    mock_db.execute.return_value.scalar.return_value = -10 # Negative balance
    
    mocker.patch("main.SessionLocal", return_value=mock_db)
    
    response = client.post(
        "/transfer",
        params={"from_acct": "A", "to_acct": "B", "amount": 100.0},
        headers={"idempotency-key": "key456"}
    )
    
    assert response.status_code == 400
    assert "Insufficient funds" in response.json()["detail"]
    assert mock_db.rollback.call_count >= 1
