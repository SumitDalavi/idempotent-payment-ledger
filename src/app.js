const express = require('express');
const crypto = require('crypto');

const app = express();
app.use(express.json());

// In-memory mock database
const processedPayments = new Map();
const ledger = [];

app.post('/api/v1/payments', (req, res) => {
  const idempotencyKey = req.headers['idempotency-key'];
  
  if (!idempotencyKey) {
    return res.status(400).json({ error: 'Idempotency-Key header is required' });
  }

  const { amount, currency, accountId } = req.body;

  if (!amount || !currency || !accountId) {
    return res.status(400).json({ error: 'Missing required payment fields' });
  }

  // Check if this payment was already processed
  if (processedPayments.has(idempotencyKey)) {
    const existingResult = processedPayments.get(idempotencyKey);
    return res.status(200).json({
      message: 'Payment previously processed',
      status: 'success',
      transactionId: existingResult.transactionId,
      cached: true
    });
  }

  // Process new payment
  const transactionId = crypto.randomUUID();
  const paymentRecord = {
    transactionId,
    amount,
    currency,
    accountId,
    timestamp: new Date().toISOString()
  };

  // Save to ledger and cache result against idempotency key
  ledger.push(paymentRecord);
  processedPayments.set(idempotencyKey, paymentRecord);

  return res.status(201).json({
    message: 'Payment processed successfully',
    status: 'success',
    transactionId,
    cached: false
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', ledgerSize: ledger.length });
});

module.exports = app;

if (require.main === module) {
  const port = process.env.PORT || 3000;
  app.listen(port, () => console.log(`Payment Ledger running on port ${port}`));
}
