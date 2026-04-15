from faststream.rabbit import RabbitBroker, RabbitExchange, RabbitQueue

broker = RabbitBroker("amqp://guest:guest@rabbitmq:5672/")

payments_queue = RabbitQueue("payments.new")
dlq_queue = RabbitQueue("payments.dlq")