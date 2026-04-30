## 📦 Asynchronous Payment Processing Service

Asynchronous microservice for payment processing with guaranteed event delivery (Outbox pattern), queues, and retry logic.

---

## Documentation: README with runtime and examples

docker-compose up --build

API: http://localhost:8000/docs
RabbitMQ UI: http://localhost:15672 (guest/guest)
Postgres: localhost:5432

---

## Static API key in the X-API-Key header for all endpoints

The API key is set via environment variables.

In the current configuration (docker-compose):

API_KEY: vasxor-fYmgan-giscy2

Usage:

X-API-Key: vasxor-fYmgan-giscy2

---

## API endpoints: creating and receiving a payment
[Minimum RUB amount is 10]

### POST /api/v1/payments

Headers:

X-API-Key: vasxor-fYmgan-giscy2
Idempotency-Key: unique-key

Body:

{
"amount": 100.50,
"currency": "USD",
"description": "Test payment",
"metadata": {},
"webhook_url": "http://example.com/webhook"
}

Response:

{
"payment_id": "uuid",
"status": "pending",
"created_at": "timestamp"
}

---

### GET /api/v1/payments/{payment_id}

Response:

{
"id": "uuid",
"amount": "100.50",
"currency": "USD",
"description": "Test payment",
"metadata": {},
"status": "pending | succeeded | failed",
"idempotency_key": "string",
"webhook_url": "string",
"created_at": "timestamp",
"processed_at": "timestamp | null"
}

---

## Idempotency

- Uses Idempotency Key
- Duplicate protection via UNIQUE index
- When retrying:
- an existing payment is returned
- data is not overwritten

API → DB (payment + outbox) → Outbox Dispatcher → RabbitMQ → Consumer → DB → Webhook

---

## Outbox pattern: guaranteed event delivery

### Avoid event loss between:
- DB commit
- sending to RabbitMQ

1. In a single transaction:
- Payment
- OutboxEvent

2. Dispatcher:
- reads pending events
- sends to RabbitMQ
- marks as sent

✔ event won't be lost
✔ eventual consistency

---

## Messaging

Queues:

payments.new — payment processing

payments.dlq — failed events

Broker: RabbitMQ (FastStream)

---

## Consumer: one handler that does everything

Behavior:

- delay: 2–5 sec
- success: 90%
- failure: 10%

Actions:

1. Receives event
2. Finds payment
3. Updates status:
- succeeded / failed
4. Writes processed_at
5. Sends webhook

---

## Retry: 3 attempts with exponential backoff

### Outbox

- max: 3 attempts
- backoff: 2^attempt (2, 4, 8 sec)
- after → DLQ

### Webhook

- 3 attempts
- exponential backoff
- errors are logged

---

## Dead Letter Queue: for permanently dropped messages

If event not processed:

→ sent to payments.dlq

Causes:
- permanent errors
- corrupted data
- consumer issues

---

## Models and Migrations: payments and outbox

###payments

- id (UUID, PK)
- amount (Decimal)
- currency (Enum)
- description
- metadata (JSON)
- status (pending/succeeded/failed)
- idempotency_key (UNIQUE)
- webhook_url
- created_at
- processed_at

---

###outbox

- id (UUID)
- event_type
- payload (JSON)
- status (pending/sent/dlq)
- attempts
- next_retry_at
- last_error
- sent_at
- created_at

---

## Docker: compose file with postgres, rabbitmq, api, consumer

Services:

- api — FastAPI application
- consumer — queue handler
- db - PostgreSQL
- rabbitmq - broker Messages

---

## Scenarios:

1. API crashed after commit
→ Outbox will still be sent

2. RabbitMQ is unavailable
→ Dispatcher retry

3. Consumer crashed
→ Message will remain in the queue

4. Webhook is not responding
→ retry → log → ignore

---

## Documentation: README with startup and examples

curl -X POST http://localhost:8000/api/v1/payments \
-H "X-API-Key: vasxor-fYmgan-giscy2" \
-H "Idempotency-Key: test-123" \
-H "Content-Type: application/json" \
-d '{
"amount": 10,
"currency": "USD",
"description": "test", 
"webhook_url": "http://webhook.site/test" 
}'
