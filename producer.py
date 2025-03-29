import aio_pika
import os
from schemas.notification import NotificationRequest, RecipientType
import asyncio
from utils.task import TaskService
from services.groups import get_users_in_group

class RabbitMQConnectionPool:
    def __init__(self, pool_size=5):
        self.pool_size = pool_size
        self._connection_pool = asyncio.Queue(maxsize=pool_size)
        self._channel_pool = asyncio.Queue(maxsize=pool_size)

    async def initialize(self):
        rabbitmq_user = os.getenv('RABBITMQ_DEFAULT_USER')
        rabbitmq_pass = os.getenv('RABBITMQ_DEFAULT_PASS')
        credentials = aio_pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)

        for _ in range(self.pool_size):
            connection = await aio_pika.connect_robust(
                f"amqp://{rabbitmq_user}:{rabbitmq_pass}@localhost/",
                loop=asyncio.get_event_loop()
            )
            self._connection_pool.put_nowait(connection)
            self._channel_pool.put_nowait(await connection.channel())

    async def get_connection(self):
        return await self._connection_pool.get()

    async def return_connection(self, connection):
        await self._connection_pool.put(connection)

    async def get_channel(self):
        return await self._channel_pool.get()

    async def return_channel(self, channel):
        await self._channel_pool.put(channel)


async def send_webpush(request: NotificationRequest):
    pool = RabbitMQConnectionPool()
    channel = await pool.get_channel()

    await channel.declare_queue('webpush_notifications', arguments={'x-max-priority': 10})

    if request.recipient_type == RecipientType.SINGLE:
        message = {
            "type": request.type,
            "payload": request.payload,
            "recipient": request.recipient,
            "priority": request.priority
        }
        
        await channel.default_exchange.publish(
            aio_pika.Message(body=str(message).encode(), priority=request.priority),
            routing_key='webpush_notifications'
        )
        
    elif request.recipient_type == RecipientType.GROUP:
        task_service = TaskService()
        task_service.add_task(send_group_notifications, request)
        background_tasks = task_service.get_tasks()
        await background_tasks()

    await pool.return_channel(channel)

async def send_group_notifications(request: NotificationRequest):
    users = get_users_in_group(request.recipient)
    pool = RabbitMQConnectionPool()
    channel = await pool.get_channel()

    for user in users:
        message = {
            "type": request.type,
            "payload": request.payload,
            "recipient": user['id'],
            "priority": request.priority
        }

        await channel.default_exchange.publish(
            aio_pika.Message(body=str(message).encode(), priority=request.priority),
            routing_key='webpush_notifications'
        )

    await pool.return_channel(channel)
