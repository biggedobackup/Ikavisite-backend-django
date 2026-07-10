from django.apps import AppConfig


class VisitesConfig(AppConfig):
    name = 'visites'

    def ready(self):
        from core.signals import connect_signals
        connect_signals()
