from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
from config import config
from database.models import Role, Appointment, AppointmentStatus, Specialist, User


def get_client_keyboard() -> ReplyKeyboardMarkup:
    """
    Returns a reply keyboard for clients with actions.

    Includes buttons for creating, viewing, and canceling appointments.
    """
    buttons = [
        [KeyboardButton(text="📝 Новая заявка")],
        [KeyboardButton(text="📋 Мои заявки")],
        [KeyboardButton(text="🚫 Отменить заявку")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """
    Returns a reply keyboard for admins with actions.

    Provides access to statistics, appointments, blacklist, specialist management, and reassignment.
    """
    buttons = [
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📅 Записи")],
        [KeyboardButton(text="🔨 ЧС"), KeyboardButton(text="🔨 работа с ЧС")],
        [KeyboardButton(text="👥 Специалисты"), KeyboardButton(text="📄 Экспорт данных")],
        [KeyboardButton(text="📋 Назначенные встречи")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_admin_inline_keyboard() -> InlineKeyboardMarkup:
    """
    Returns an inline keyboard for admin actions.

    Includes navigation and cancellation options.
    """
    buttons = [
        [InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_export")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_specialist_keyboard(has_appointments: bool = False) -> ReplyKeyboardMarkup:
    """
    Returns a reply keyboard for specialists, including 'Готов к работе' if has_appointments=True.

    Dynamically adjusts based on active appointments.
    """
    buttons = []
    if has_appointments:
        buttons.append([KeyboardButton(text="✅ Готов к работе")])
    buttons.extend([
        [KeyboardButton(text="📅 Расписание")],
        [KeyboardButton(text="📊 Отчеты")],
        [KeyboardButton(text="📈 Мой ранг")]
    ])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_specialist_active_keyboard() -> ReplyKeyboardMarkup:
    """
    Returns a reply keyboard for specialists during an active appointment.

    Includes options to close or cancel the appointment.
    """
    buttons = [
        [KeyboardButton(text="✅ Закрыть заявку")],
        [KeyboardButton(text="❌ Отменить встречу")],
        [KeyboardButton(text="📅 Расписание")],
        [KeyboardButton(text="📊 Отчеты")],
        [KeyboardButton(text="📈 Мой ранг")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def get_report_period_keyboard() -> InlineKeyboardMarkup:
    """
    Returns an inline keyboard for selecting report periods.

    Offers weekly, monthly, and quarterly report options.
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="За неделю", callback_data="report_period:week")],
        [InlineKeyboardButton(text="За месяц", callback_data="report_period:month")],
        [InlineKeyboardButton(text="За 3 месяца", callback_data="report_period:3months")]
    ])


def get_time_selection_keyboard(appointments: list, proposed_date: datetime) -> InlineKeyboardMarkup:
    """
    Returns an inline keyboard for selecting time slots, with available and occupied slots.

    Args:
        appointments: List of Appointment objects to check for occupied slots.
        proposed_date: Datetime object for the selected date.
    """
    if not isinstance(appointments, list):
        appointments = []
    if not isinstance(proposed_date, datetime):
        raise ValueError("proposed_date must be a datetime object")

    time_slots = []
    current_time = datetime(proposed_date.year, proposed_date.month, proposed_date.day, 9, 0)
    morning_end = datetime(proposed_date.year, proposed_date.month, proposed_date.day, 11, 30)
    while current_time <= morning_end:
        time_slots.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=30)

    current_time = datetime(proposed_date.year, proposed_date.month, proposed_date.day, 13, 30)
    evening_end = datetime(proposed_date.year, proposed_date.month, proposed_date.day, 17, 30)
    while current_time <= evening_end:
        time_slots.append(current_time.strftime("%H:%M"))
        current_time += timedelta(minutes=30)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    row = []
    for slot in time_slots:
        slot_datetime = datetime.strptime(
            f"{proposed_date.strftime('%Y-%m-%d')} {slot}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=config.TIMEZONE)
        is_taken = False
        specialist_name = None
        appointment_id = None
        for app in appointments:
            if (app.status == AppointmentStatus.APPROVED and
                    app.scheduled_time and
                    app.scheduled_time.astimezone(config.TIMEZONE).strftime("%Y-%m-%d %H:%M") ==
                    slot_datetime.strftime("%Y-%m-%d %H:%M")):
                is_taken = True
                specialist_name = app.specialist.full_name if app.specialist else "Неизвестный специалист"
                appointment_id = app.id
                break

        if is_taken:
            button_text = f"🔴 {slot} ({specialist_name})"
            button = InlineKeyboardButton(text=button_text, callback_data=f"occupied_{appointment_id}")
        else:
            button_text = f"🟢 {slot}"
            button = InlineKeyboardButton(text=button_text, callback_data=f"time_{slot}")

        row.append(button)
        if len(row) == 3:
            keyboard.inline_keyboard.append(row)
            row = []

    if row:
        keyboard.inline_keyboard.append(row)

    keyboard.inline_keyboard.append([InlineKeyboardButton(text="Отмена", callback_data="cancel_time_selection")])
    return keyboard


def get_schedule_pagination_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """
    Returns an inline keyboard for schedule pagination with 'Previous' and 'Next' buttons.

    Args:
        page: Current page number (0-based).
        total_pages: Total number of pages.
    """
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="schedule_prev"))
    if page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text="➡️ Далее", callback_data="schedule_next"))
    return InlineKeyboardMarkup(inline_keyboard=[buttons] if buttons else [])


def get_appointment_actions_keyboard(appointment_id: int) -> InlineKeyboardMarkup:
    """
    Returns an inline keyboard for appointment actions like cancellation and confirmation.

    Args:
        appointment_id: ID of the appointment.
    """
    buttons = [
        [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_appointment_{appointment_id}")],
        [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{appointment_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)