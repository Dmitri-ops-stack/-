from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.models import Appointment, AppointmentStatus
from datetime import datetime
from config import config
from utils.helpers import format_appointment_date
import logging

logger = logging.getLogger(__name__)

def escape_markdown_v2(text: any) -> str:
    """Escape special characters for Telegram MarkdownV2, handling None or non-string inputs."""
    if text is None:
        return ""
    text = str(text)
    chars_to_escape = r'_*[]()~`#+-=|{}.!'
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
    return text

async def notify_specialist(bot: Bot, appointment: Appointment, is_reassignment: bool = False):
    """
    Notify specialist about new or reassigned appointment.
    Args:
        bot (Bot): Bot instance for sending messages.
        appointment (Appointment): Appointment object.
        is_reassignment (bool): Whether this is a reassignment notification.
    """
    specialist = appointment.specialist
    client = appointment.client
    scheduled_time = format_appointment_date(appointment.scheduled_time)
    prefix = "🔄 Переназначена заявка" if is_reassignment else "📬 Новая заявка"
    client_link = f"https://t.me/{client.user.telegram_id}"
    client_contact = f"Контакт клиента: \\[{client_link}\\]"
    try:
        chat = await bot.get_chat(client.user.telegram_id)
        if chat.username:
            client_link = f"https://t.me/{chat.username}"
            client_contact = f"Контакт клиента: \\[{client_link}\\]"
        else:
            client_contact += f"\n(Если ссылка не работает, свяжитесь с администратором: https://t.me/{config.ADMIN_ID})"
    except Exception as e:
        logger.warning(f"Cannot get username for client {client.user.telegram_id} (appointment_id: {appointment.id}): {e}")
        client_contact += f"\n(Если ссылка не работает, свяжитесь с администратором: https://t.me/{config.ADMIN_ID})"
    message_lines = [
        escape_markdown_v2(f"{prefix} #{appointment.id}"),
        escape_markdown_v2(f"👤 Клиент: {client.full_name}"),
        escape_markdown_v2(f"{client_contact}"),
        escape_markdown_v2(f"📞 Номер телефона: {client.phone or 'Не указан'}"),
        escape_markdown_v2(f"⏰ Время: {scheduled_time}"),
        escape_markdown_v2(f"🏋️ Комплекс: {appointment.complex or 'Не указан'}"),
        escape_markdown_v2(f"📝 Причина: {appointment.reason}")
    ]
    try:
        await bot.send_message(
            specialist.user_id,
            "\n".join(message_lines),
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )
        logger.info(f"Notified specialist {specialist.user_id} about {'reassigned' if is_reassignment else 'new'} appointment {appointment.id}")
    except Exception as e:
        logger.error(f"Failed to notify specialist {specialist.user_id} for appointment {appointment.id}: {e}")
        await bot.send_message(
            config.ADMIN_ID,
            escape_markdown_v2(f"Ошибка: Не удалось уведомить специалиста {specialist.full_name} о {'переназначении' if is_reassignment else 'новой'} заявке #{appointment.id}."),
            parse_mode="MarkdownV2"
        )

async def notify_client_rejected(bot: Bot, appointment: Appointment, reason: str):
    """
    Notify client about rejected appointment.
    Args:
        bot (Bot): Bot instance for sending messages.
        appointment (Appointment): Appointment object.
        reason (str): Reason for rejection.
    """
    client = appointment.client
    message_lines = [
        escape_markdown_v2(f"❌ Ваша заявка #{appointment.id} была отклонена."),
        escape_markdown_v2(f"📝 Причина: {reason}")
    ]
    try:
        await bot.send_message(
            client.user.telegram_id,
            "\n".join(message_lines),
            parse_mode="MarkdownV2"
        )
        logger.info(f"Notified client {client.user.telegram_id} about rejected appointment {appointment.id}")
    except Exception as e:
        logger.error(f"Failed to notify client {client.user.telegram_id} for rejected appointment {appointment.id}: {e}")
        await bot.send_message(
            config.ADMIN_ID,
            escape_markdown_v2(f"Ошибка: Не удалось уведомить клиента {client.full_name} об отклонении заявки #{appointment.id}."),
            parse_mode="MarkdownV2"
        )

async def notify_reminder(bot: Bot, appointment: Appointment):
    """
    Send reminders to client and specialist one hour before the appointment.
    Client gets a 'Готов к работе' button; specialist is prompted to use the schedule.
    Args:
        bot (Bot): Bot instance for sending messages.
        appointment (Appointment): Appointment object.
    """
    if appointment.status != AppointmentStatus.APPROVED:
        return
    client = appointment.client
    specialist = appointment.specialist
    scheduled_time = format_appointment_date(appointment.scheduled_time)
    # Client reminder
    if not appointment.client_ready:
        username = specialist.username
        phone = getattr(specialist, 'phone', None)
        phone_display = escape_markdown_v2(f"Телефон специалиста: {phone}") if phone and phone.strip() else "Телефон специалиста: не указан"
        if username and username.strip():
            if not username.startswith('@'):
                username = f"@{username}"
            specialist_link = f"https://t.me/{username}"
            specialist_contact = f"[Связаться со специалистом]({specialist_link})"
        else:
            specialist_link = f"https://t.me/{config.ADMIN_ID}"
            specialist_contact = f"[Связаться с администратором]({specialist_link})"
            logger.warning(f"Specialist {specialist.full_name} (ID: {specialist.user_id}, appointment_id: {appointment.id}) has no valid username.")
        client_message_lines = [
            escape_markdown_v2(f"⏰ Напоминание: ваша заявка #{appointment.id} через час в {scheduled_time}!"),
            escape_markdown_v2(f"👨‍⚕️ Специалист: {specialist.full_name}"),
            phone_display,
            specialist_contact,
            escape_markdown_v2("Подтвердите готовность к работе:")
        ]
        if not username or not username.strip():
            client_message_lines.append(f"Если не можете связаться со специалистом, обратитесь к администратору: [Администратор](https://t.me/{config.ADMIN_ID})")
        try:
            await bot.send_message(
                client.user.telegram_id,
                "\n".join(client_message_lines),
                parse_mode="MarkdownV2",
                disable_web_page_preview=True,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Готов к работе", callback_data=f"client_ready_{appointment.id}")]
                ])
            )
            logger.info(f"Sent reminder to client {client.user.telegram_id} for appointment {appointment.id}")
        except Exception as e:
            logger.error(f"Failed to send reminder to client {client.user.telegram_id} for appointment {appointment.id}: {e}")
            await bot.send_message(
                config.ADMIN_ID,
                escape_markdown_v2(f"Ошибка: Не удалось отправить напоминание клиенту {client.full_name} о заявке #{appointment.id}."),
                parse_mode="MarkdownV2"
            )
    # Specialist reminder
    if not appointment.specialist_ready:
        client_link = f"https://t.me/{client.user.telegram_id}"
        client_contact = f"Контакт клиента: \\[{client_link}\\]"
        try:
            chat = await bot.get_chat(client.user.telegram_id)
            if chat.username:
                client_link = f"https://t.me/{chat.username}"
                client_contact = f"Контакт клиента: \\[{client_link}\\]"
            else:
                client_contact += f"\n(Если ссылка не работает, свяжитесь с администратором: https://t.me/{config.ADMIN_ID})"
        except Exception as e:
            logger.warning(f"Cannot get username for client {client.user.telegram_id} (appointment_id: {appointment.id}): {e}")
            client_contact += f"\n(Если ссылка не работает, свяжитесь с администратором: https://t.me/{config.ADMIN_ID})"
        specialist_message_lines = [
            escape_markdown_v2(f"⏰ Напоминание: заявка #{appointment.id} через час в {scheduled_time}!"),
            escape_markdown_v2(f"👤 Клиент: {client.full_name}"),
            escape_markdown_v2(f"{client_contact}"),
            escape_markdown_v2(f"📞 Номер телефона: {client.phone or 'Не указан'}"),
            escape_markdown_v2(f"🏋️ Комплекс: {appointment.complex or 'Не указан'}"),
            escape_markdown_v2(f"📝 Причина: {appointment.reason}"),
            escape_markdown_v2("Подтвердите готовность в расписании.")
        ]
        try:
            await bot.send_message(
                specialist.user_id,
                "\n".join(specialist_message_lines),
                parse_mode="MarkdownV2",
                disable_web_page_preview=True
            )
            logger.info(f"Sent reminder to specialist {specialist.user_id} for appointment {appointment.id}")
        except Exception as e:
            logger.error(f"Failed to send reminder to specialist {specialist.user_id} for appointment {appointment.id}: {e}")
            await bot.send_message(
                config.ADMIN_ID,
                escape_markdown_v2(f"Ошибка: Не удалось отправить напоминание специалисту {specialist.full_name} о заявке #{appointment.id}."),
                parse_mode="MarkdownV2"
            )

async def notify_client_reassigned(bot: Bot, appointment: Appointment):
    """
    Notify client about reassigned appointment with specialist details and action buttons.
    Args:
        bot (Bot): Bot instance for sending messages.
        appointment (Appointment): Appointment object.
    """
    client = appointment.client
    specialist = appointment.specialist
    scheduled_time = format_appointment_date(appointment.scheduled_time)
    username = specialist.username
    phone = getattr(specialist, 'phone', None)
    phone_display = escape_markdown_v2(f"Телефон специалиста: {phone}") if phone and phone.strip() else "Телефон специалиста: не указан"
    if username and username.strip():
        if not username.startswith('@'):
            username = f"@{username}"
        specialist_link = f"https://t.me/{username}"
        specialist_contact = f"[Связаться со специалистом]({specialist_link})"
    else:
        specialist_link = f"https://t.me/{config.ADMIN_ID}"
        specialist_contact = f"[Связаться с администратором]({specialist_link})"
        logger.warning(f"Specialist {specialist.full_name} (ID: {specialist.user_id}, appointment_id: {appointment.id}) has no valid username.")
    message_lines = [
        escape_markdown_v2(f"🔄 Ваша заявка #{appointment.id} была переназначена!"),
        escape_markdown_v2(f"👨‍⚕️ Новый специалист: {specialist.full_name}"),
        phone_display,
        specialist_contact,
        escape_markdown_v2(f"⏰ Дата и время: {scheduled_time}")
    ]
    if not username or not username.strip():
        message_lines.append(f"Если не можете связаться со специалистом, обратитесь к администратору: [Администратор](https://t.me/{config.ADMIN_ID})")
    try:
        await bot.send_message(
            client.user.telegram_id,
            "\n".join(message_lines),
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Одобрить", callback_data=f"client_approve_{appointment.id}"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data=f"client_decline_{appointment.id}")
                ]
            ])
        )
        logger.info(f"Notified client {client.user.telegram_id} about reassigned appointment {appointment.id}")
    except Exception as e:
        logger.error(f"Failed to notify client {client.user.telegram_id} for reassigned appointment {appointment.id}: {e}")
        await bot.send_message(
            config.ADMIN_ID,
            escape_markdown_v2(f"Ошибка: Не удалось уведомить клиента {client.full_name} о переназначении заявки #{appointment.id}."),
            parse_mode="MarkdownV2"
        )