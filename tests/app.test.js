const request = require('supertest');
const app = require('../src/app');

describe('Idempotent Payment Ledger API', () => {
  it('should return 400 if Idempotency-Key header is missing', async () => {
    const res = await request(app)
      .post('/api/v1/payments')
      .send({ amount: 100, currency: 'USD', accountId: 'acc_123' });
    
    expect(res.statusCode).toEqual(400);
    expect(res.body.error).toEqual('Idempotency-Key header is required');
  });

  it('should return 400 if required fields are missing', async () => {
    const res = await request(app)
      .post('/api/v1/payments')
      .set('Idempotency-Key', 'key-1')
      .send({ amount: 100 });
    
    expect(res.statusCode).toEqual(400);
    expect(res.body.error).toEqual('Missing required payment fields');
  });

  it('should process a new payment', async () => {
    const res = await request(app)
      .post('/api/v1/payments')
      .set('Idempotency-Key', 'key-2')
      .send({ amount: 100, currency: 'USD', accountId: 'acc_123' });
    
    expect(res.statusCode).toEqual(201);
    expect(res.body.message).toEqual('Payment processed successfully');
    expect(res.body.cached).toEqual(false);
    expect(res.body.transactionId).toBeDefined();
  });

  it('should return cached result for duplicate idempotency key', async () => {
    // First request
    const res1 = await request(app)
      .post('/api/v1/payments')
      .set('Idempotency-Key', 'key-3')
      .send({ amount: 200, currency: 'EUR', accountId: 'acc_456' });
    
    expect(res1.statusCode).toEqual(201);
    
    // Duplicate request
    const res2 = await request(app)
      .post('/api/v1/payments')
      .set('Idempotency-Key', 'key-3')
      .send({ amount: 200, currency: 'EUR', accountId: 'acc_456' });
    
    expect(res2.statusCode).toEqual(200);
    expect(res2.body.message).toEqual('Payment previously processed');
    expect(res2.body.cached).toEqual(true);
    expect(res2.body.transactionId).toEqual(res1.body.transactionId);
  });

  it('should return health check', async () => {
    const res = await request(app).get('/health');
    expect(res.statusCode).toEqual(200);
    expect(res.body.status).toEqual('healthy');
  });
});
