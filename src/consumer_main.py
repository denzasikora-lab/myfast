import asyncio
from src.broker import broker


async def main():
    for i in range(10):
        try:
            await broker.start()
            break
        except Exception:
            print(f"Rabbit not ready, retry {i}...")
            await asyncio.sleep(2)
    else:
        raise RuntimeError("Failed to connect to RabbitMQ")

    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())