import re
from datetime import datetime
from config import config
import logging

logger = logging.getLogger(__name__)


def validate_phone(phone: str) -> bool:
    """
    Проверяет, соответствует ли номер телефона формату: +7 или 8 и 10 цифр.
    Args:
        phone: Номер телефона для проверки.
    Returns:
        True, если номер валиден, иначе False.
    """
    pattern = r"^(?:\+7|8)\d{10}$"
    is_valid = bool(re.match(pattern, phone))
    if not is_valid:
        logger.warning(f"Invalid phone number: {phone}")
    return is_valid


def validate_date(date_str: str) -> datetime:
    """
    Проверяет, является ли дата валидной, не в прошлом и не в выходные.
    Args:
        date_str: Строка даты в формате ДД.ММ.ГГГГ.
    Returns:
        datetime: Объект datetime в часовом поясе config.TIMEZONE.
    Raises:
        ValueError: Если формат неверный, дата в прошлом или выходной.
    """
    try:
        # Парсим дату в формате DD.MM.YYYY
        date = datetime.strptime(date_str, "%d.%m.%Y").replace(tzinfo=config.TIMEZONE)
        now = datetime.now(tz=config.TIMEZONE).replace(hour=0, minute=0, second=0, microsecond=0)

        # Проверяем, что дата не в прошлом
        if date.date() < now.date():
            logger.warning(f"Date in the past: {date_str}")
            raise ValueError("Дата не может быть в прошлом")

        # Проверяем, что дата — рабочий день (понедельник–пятница)
        # Можно убрать, если выходные разрешены
        if date.weekday() >= 5:
            logger.warning(f"Date is a weekend: {date_str}")
            raise ValueError("Запись возможна только в рабочие дни (пн-пт)")

        # Рабочие часы не проверяем, так как они применимы к scheduled_time
        logger.debug(f"Validated date: {date_str}")
        return date

    except ValueError as e:
        if "strptime" in str(e):
            logger.warning(f"Invalid date format: {date_str}")
            raise ValueError("Неверный формат даты. Используйте ДД.ММ.ГГГГ (например, 31.12.2025)")
        raise


def format_appointment_date(dt: datetime) -> str:
    """
    Форматирует дату и время в строку формата ДД.ММ.ГГГГ ЧЧ:ММ.
    Args:
        dt: Объект datetime.
    Returns:
        Форматированная строка.
    """
    return dt.strftime("%d.%m.%Y %H:%M")