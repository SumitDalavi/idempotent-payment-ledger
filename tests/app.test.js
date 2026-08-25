const request = require('supertest');
const app = require('../src/app');

describe('Payment Ledger API', () => {
  it('should reject payment without idempotency key', async () => {
    const res = await request(app)
      .post('/api/v1/payments')
      .send({ amount: 100, currency: 'USD', accountId: '123' });
      
    expect(res.statusCode).toBe(400);
    expect(res.body.error).toBe('Idempotency-Key header is required');
  });

  it('should process a new payment successfully', async () => {
    const idempotencyKey = 'test-key-1';
    const res = await request(app)
      .post('/api/v1/payments')
      .set('Idempotency-Key', idempotencyKey)
      .send({ amount: 100, currency: 'USD', accountId: '123' });
      
    expect(res.statusCode).toBe(201);
    expect(res.body.cached).toBe(false);
    expect(res.body.transactionId).toBeDefined();
  });

  it('should return cached response for duplicate idempotency key', async () => {
    const idempotencyKey = 'test-key-2';
    const payload = { amount: 50, currency: 'EUR', accountId: '456' };
    
    // First request
    const res1 = await request(app)
      .post('/api/v1/payments')
      .set('Idempotency-Key', idempotencyKey)
      .send(payload);
      
    expect(res1.statusCode).toBe(201);
    
    // Duplicate request
    const res2 = await request(app)
      .post('/api/v1/payments')
      .set('Idempotency-Key', idempotencyKey)
      .send(payload);
      
    expect(res2.statusCode).toBe(200);
    expect(res2.body.cached).toBe(true);
    expect(res2.body.transactionId).toBe(res1.body.transactionId);
  });
});
