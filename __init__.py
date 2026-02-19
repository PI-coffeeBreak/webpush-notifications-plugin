from coffeebreak import MessageBus
from .router import router
from .producer import send_webpush
import logging

logger = logging.getLogger("coffeebreak.webpush-notifications")


async def REGISTER():
    message_bus = MessageBus()
    message_bus.register_message_handler("webpush", send_webpush)
    message_bus.register_message_handler("in-app", send_webpush)
    logger.info("Web Push Notifications Plugin registered")


async def UNREGISTER():
    message_bus = MessageBus()
    message_bus.unregister_message_handler("webpush", send_webpush)
    message_bus.unregister_message_handler("in-app", send_webpush)
    logger.info("Web Push Notifications Plugin unregistered")
