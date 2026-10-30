from django.apps import AppConfig


class CoreAppConfig(AppConfig):
    name = 'core_app'

    def ready(self):
        from . import signals  # noqa: F401  (acceso por empresa al ligar usuario a empleado)
