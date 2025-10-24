from coffeebreak import MessageBus
from .router import router
from .producer import send_webpush
import logging

logger = logging.getLogger("coffeebreak.webpush-notifications")

IDENTIFIER = "webpush-notifications"
NAME = "Web Push Notifications Plugin"
DESCRIPTION = "A plugin for sending web push notifications"

async def register_plugin():
    message_bus = MessageBus()
    message_bus.register_message_handler("webpush", send_webpush)
    message_bus.register_message_handler("in-app", send_webpush)
    logger.info("Web Push Notifications Plugin registered")

async def unregister_plugin():
    message_bus = MessageBus()
    message_bus.unregister_message_handler("webpush", send_webpush)
    message_bus.unregister_message_handler("in-app", send_webpush)
    logger.info("Web Push Notifications Plugin unregistered")

REGISTER = register_plugin
UNREGISTER = unregister_plugin
