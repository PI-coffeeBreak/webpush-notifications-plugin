from services.message_bus import MessageBus
from .router import router
from .producer import send_webpush

def register_plugin():
    MessageBus().register_message_handler("webpush", send_webpush)

def unregister_plugin():
    MessageBus().unregister_message_handler("webpush", send_webpush)



REGISTER = register_plugin
UNREGISTER = register_plugin