import aio_pika
import os
import logging
import json
from typing import Optional, Dict, Any
from schemas.notification import NotificationRequest, RecipientType
import asyncio
from utils.task import TaskService
from services.groups import get_users_in_group

logger = logging.getLogger("coffeebreak.webpush")


class RabbitMQConnectionPool:
    _instance: Optional['RabbitMQConnectionPool'] = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, pool_size=5):
        if not self._initialized:
            self.pool_size = pool_size
            self._connection_pool = asyncio.Queue(maxsize=pool_size)
            self._channel_pool = asyncio.Queue(maxsize=pool_size)
            self._initialized = True

    async def initialize(self):
        if self._connection_pool.qsize() > 0:
            return

        rabbitmq_user = os.getenv('RABBITMQ_DEFAULT_USER', 'username')
        rabbitmq_pass = os.getenv('RABBITMQ_DEFAULT_PASS', 'password')
        rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
        rabbitmq_port = os.getenv('RABBITMQ_PORT', '5672')

        host = rabbitmq_host
        connection = None

        try:
            connection = await aio_pika.connect_robust(
                f"amqp://{rabbitmq_user}:{rabbitmq_pass}@{host}:{rabbitmq_port}/",
                loop=asyncio.get_event_loop(),
                timeout=5
            )
            logger.info(f"Successfully connected to RabbitMQ at {host}")
        except Exception as e:
            logger.warning(
                f"Failed to connect to RabbitMQ at {host}: {str(e)}")
            return

        for _ in range(self.pool_size):
            try:
                if _ > 0:
                    connection = await aio_pika.connect_robust(
                        str(connection.url),
                        loop=asyncio.get_event_loop(),
                        timeout=5
                    )

                channel = await connection.channel()
                await channel.set_qos(prefetch_count=1)

                await channel.declare_queue(
                    'webpush_queue',
                    durable=True,
                    arguments={
                        'x-max-priority': 10,
                        'x-message-ttl': 24 * 60 * 60 * 1000
                    }
                )

                self._connection_pool.put_nowait(connection)
                self._channel_pool.put_nowait(channel)
                logger.info(
                    f"Initialized RabbitMQ connection {_ + 1}/{self.pool_size}")
            except Exception as e:
                logger.error(
                    f"Failed to initialize RabbitMQ connection: {str(e)}")
                raise

    async def get_channel(self) -> aio_pika.Channel:
        if self._channel_pool.empty():
            await self.initialize()
        return await self._channel_pool.get()

    async def return_channel(self, channel: aio_pika.Channel):
        if not channel.is_closed:
            await self._channel_pool.put(channel)

    async def close(self):
        while not self._channel_pool.empty():
            channel = await self._channel_pool.get()
            await channel.close()

        while not self._connection_pool.empty():
            connection = await self._connection_pool.get()
            await connection.close()


def serialize_message(message: Dict[str, Any]) -> bytes:
    try:
        return json.dumps(message).encode('utf-8')
    except Exception as e:
        logger.error(f"Failed to serialize message: {str(e)}")
        raise


async def publish_message(channel: aio_pika.Channel, message: Dict[str, Any], priority: int = 0):
    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=serialize_message(message),
                    priority=priority,
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key='webpush_queue'
            )
            return
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(
                    f"Failed to publish message after {max_retries} attempts: {str(e)}")
                raise
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed: {str(e)}")
            await asyncio.sleep(retry_delay * (attempt + 1))


async def send_webpush(request: NotificationRequest):
    try:
        logger.info(f"Preparing to send webpush notification: {request}")
        pool = RabbitMQConnectionPool()
        channel = await pool.get_channel()

        try:
            # Base message structure for all types
            message = {
                "type": request.type,
                "payload": request.payload,
                "recipient": request.recipient,
                "priority": request.priority
            }

            if request.recipient_type == RecipientType.UNICAST:
                logger.info(
                    f"Sending UNICAST notification to: {message['recipient']}")
                await publish_message(channel, message, request.priority)

            elif request.recipient_type == RecipientType.MULTICAST:
                logger.info(
                    f"Sending MULTICAST notification to group: {request.recipient}")
                task_service = TaskService()
                task_service.add_task(send_group_notifications, request)
                background_tasks = task_service.get_tasks()
                await background_tasks()

            elif request.recipient_type == RecipientType.BROADCAST:
                logger.info(
                    "Sending BROADCAST notification to all subscribers")
                # Ensure recipient is None for broadcast
                message["recipient"] = None
                await publish_message(channel, message, request.priority)

        finally:
            await pool.return_channel(channel)

    except Exception as e:
        logger.error(f"Error in send_webpush: {str(e)}")
        raise


async def send_group_notifications(request: NotificationRequest):
    try:
        logger.info(f"Fetching users in group: {request.recipient}")
        users = get_users_in_group(request.recipient)

        if not users:
            logger.warning(f"No users found in group: {request.recipient}")
            return

        pool = RabbitMQConnectionPool()
        channel = await pool.get_channel()

        try:
            for user in users:
                message = {
                    "type": request.type,
                    "payload": request.payload,
                    "recipient": user['id'],
                    "priority": request.priority
                }
                await publish_message(channel, message, request.priority)
                logger.debug(f"Notification sent to user {user['id']}")

        finally:
            await pool.return_channel(channel)

    except Exception as e:
        logger.error(f"Error in send_group_notifications: {str(e)}")
        raise
