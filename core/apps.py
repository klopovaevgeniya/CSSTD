from django.apps import AppConfig


import logging

logger = logging.getLogger(__name__)

# Summary: Настраивает поведение приложения для CoreConfig.
class CoreConfig(AppConfig):
    name = 'core'
