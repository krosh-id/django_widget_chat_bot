from django.apps import AppConfig
import threading
import os

class SocialIntegrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'social_integration'

    _listener_started = False

    def ready(self):
        # Не запускать при выполнении тестов
        if os.environ.get('RUN_MAIN') != 'true' or os.environ.get('DJANGO_TEST') == 'true':
            return

        if not self._listener_started:
            self._listener_started = True
            from .services import start_vk_listeners
            threading.Thread(target=start_vk_listeners, daemon=True).start()
