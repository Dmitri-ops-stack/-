import os
from dotenv import load_dotenv
from aiogram.fsm.storage.memory import MemoryStorage
from datetime import datetime
import pytz
import logging

# Загрузка переменных окружения из .env
load_dotenv()

# Добавим логирование для отладки
logger = logging.getLogger(__name__)



        # Настройки рабочего времени
        self.WORK_HOURS = {
            "start": 9,
            "end": 18,
            "lunch_start": 12,
            "lunch_end": 14
        }
        self.TIMEZONE = pytz.timezone("Europe/Moscow")  # Используем pytz.timezone

    def validate(self):
        """Проверка корректности настроек."""
        if not (0 <= self.WORK_HOURS["start"] < self.WORK_HOURS["end"] <= 24):
            raise ValueError("Invalid work hours configuration")
        if not (self.WORK_HOURS["start"] <= self.WORK_HOURS["lunch_start"] < self.WORK_HOURS["lunch_end"] <= self.WORK_HOURS["end"]):
            raise ValueError("Invalid lunch hours configuration")

# Создание объекта конфигурации и валидация
config = Config()
config.validate()

# Настройка хранилища FSM
storage = MemoryStorage()

# Логируем загруженные значения
logger.info(f"Loaded config: BOT_TOKEN={config.BOT_TOKEN}, ADMIN_ID={config.ADMIN_ID}, CODE_WORD={config.CODE_WORD}")
