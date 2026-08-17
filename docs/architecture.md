# idempotent-payment-ledger Architecture

## System Diagram
The following Mermaid.js sequence diagram maps the core workflow and interactions:

```mermaid
sequenceDiagram
    client->>API: POST /charge
API->>DB: Check idempotency_key
DB-->>API: Status
API->>Stripe: Execute charge
API->>DB: Record transaction
API-->>client: Success
```

## Component Breakdown
- **Core Technology**: Python, Postgres
- **Design Paradigm**: Emphasizes high availability, fault tolerance, and security.

## Security & Scaling Considerations
- Strict boundary validations.
- Horizontal scalability achieved via stateless workers.
- Encrypted data at rest and in transit.
