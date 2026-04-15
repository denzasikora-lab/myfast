## 📦 Асинхронный сервис процессинга платежей

Асинхронный микрсервис для обработки платежей с гарантированной доставкой событий (Outbox pattern), очередями и retry-логикой.

---

## Доккументация: README с запуском и примерами

docker-compose up --build

API: http://localhost:8000/docs  
RabbitMQ UI: http://localhost:15672 (guest/guest)  
Postgres: localhost:5432  

---

## Статический API ключ в заголовке X-API-Key для всех эндпоинтов

API ключ задается через переменные окружения.

В текущей конфигурации (docker-compose):

API_KEY: vasxor-fYmgan-giscy2

Использование:

X-API-Key: vasxor-fYmgan-giscy2

---

## API эндпоинты: создание и получение платежа
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

## Идемпотентность

- Используется Idempotency-Key
- Защита от дублей через UNIQUE индекс
- При повторе:
  - возвращается существующий payment
  - данные не перезаписываются

API → DB (payment + outbox) → Outbox Dispatcher → RabbitMQ → Consumer → DB → Webhook

---

## Outbox pattern: гарантированная доставка событий

### Избжать потери событий между:
- DB commit
- отправкой в RabbitMQ

1. В одной транзакции:
   - Payment
   - OutboxEvent

2. Dispatcher:
   - читает pending события
   - отправляет в RabbitMQ
   - помечает как sent

✔ событие не потеряется  
✔ eventual consistency  

---

## Messaging

Queues:

payments.new — обработка платежей  
payments.dlq — неудачные события  

Broker: RabbitMQ (FastStream)

---

## Consumer: один обработчик, делающий всё

Поведение:

- delay: 2–5 sec
- success: 90%
- fail: 10%

Действия:

1. Получает событие
2. Находит payment
3. Обновляет статус:
   - succeeded / failed
4. Записывает processed_at
5. Отправляет webhook

---

## Retry: 3 попытки с экспоненциальной задержкой

### Outbox

- max: 3 attempts
- backoff: 2^attempt (2, 4, 8 сек)
- после → DLQ

### Webhook

- 3 попытки
- exponential backoff
- ошибки логируются

---

## Dead Letter Queue: для окончательно упавших сообщений

Если событие не обработано:

→ отправляется в payments.dlq

Причины:
- постоянные ошибки
- битые данные
- проблемы consumer

---

## Модели и миграции: таблицы payments и outbox

### payments

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

### outbox

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

## Docker: compose файл с postgres, rabbitmq, api, consumer

Сервисы:

- api — FastAPI приложение
- consumer — обработчик очереди
- db — PostgreSQL
- rabbitmq — брокер сообщений

---

## Сценарии:

1. API упал после commit  
   → outbox всё равно отправится

2. RabbitMQ недоступен  
   → dispatcher ретраит

3. Consumer упал  
   → сообщение останется в очереди

4. Webhook не отвечает  
   → retry → лог → ignore

---

## Документация: README с запуском и примерами

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
