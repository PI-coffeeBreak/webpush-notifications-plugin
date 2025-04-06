from services.message_bus import MessageBus
from .router import router
from .producer import send_webpush


async def register_plugin():
    message_bus = MessageBus()
    await message_bus.register_message_handler("webpush", send_webpush)
    await message_bus.register_message_handler("in-app", send_webpush)


async def unregister_plugin():
    message_bus = MessageBus()
    await message_bus.unregister_message_handler("webpush", send_webpush)
    await message_bus.unregister_message_handler("in-app", send_webpush)


REGISTER = register_plugin
UNREGISTER = unregister_plugin
