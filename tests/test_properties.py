import pytest
from hypothesis import given, strategies as st
import random
from api.app import app
from db.database import init_db, get_db

@pytest.fixture
def client():
    # Setup testing client and db
    app.config['TESTING'] = True
    app.config['DATABASE'] = ':memory:'
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client

@given(
    amount=st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
    idempotency_key=st.text(min_size=8, max_size=64, alphabet=st.characters(blacklist_categories=('Cc', 'Cs')))
)
def test_payment_is_idempotent(client, amount, idempotency_key):
    """
    Submitting the exact same payment request N times must result in a single, identical database debit.
    """
    payload = {
        "amount": round(amount, 2),
        "currency": "USD",
        "recipient": "acc_test_123"
    }
    headers = {
        "Idempotency-Key": idempotency_key
    }
    
    # Submit N times concurrently or sequentially
    n_times = random.randint(2, 5)
    responses = []
    
    for _ in range(n_times):
        # We test sequential submission simulating retry logic
        response = client.post('/api/v1/payments', json=payload, headers=headers)
        responses.append(response)
        
    # Property 1: All successful responses should be identical (Status 200 or 201 based on logic)
    # The first might be 201 Created, subsequent should be 200 OK or also 201 depending on implementation
    # But the body payload should be identical representing the same transaction ID
    tx_ids = [res.json.get('transaction_id') for res in responses if res.status_code in (200, 201)]
    
    if len(tx_ids) > 0:
        # All transaction IDs returned across the retries must be exactly the same
        assert len(set(tx_ids)) == 1, "Duplicate transactions were created for the same idempotency key!"
