from aiogram import Router, F
from aiogram.filters import Command
from typing import Optional
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Role, Appointment, AppointmentStatus
from database.crud import CRUD
from config import config
from keyboards import get_specialist_keyboard, get_specialist_active_keyboard, get_report_period_keyboard, get_schedule_pagination_keyboard
from utils.states import SpecialistStates
from utils.helpers import format_appointment_date
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = Router()

def escape_markdown_v2(text: any) -> str:
    """Escape special characters for Telegram MarkdownV2, handling None or non-string inputs."""
    if text is None:
        return ""
    text = str(text)
    chars_to_escape = r'_*[]()~`#+-=|{}.!'
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
    return text

async def has_active_appointment(session: AsyncSession, specialist_id: int) -> tuple[bool, Optional[int]]:
    """Check if the specialist has an APPROVED appointment within ±15 minutes of now."""
    crud = CRUD(session)
    now = datetime.now(tz=config.TIMEZONE)
    time_window_start = now - timedelta(minutes=15)
    time_window_end = now + timedelta(minutes=15)
    appointments = await crud.get_appointments_by_specialist(specialist_id)
    for app in appointments:
        if (app.status == AppointmentStatus.APPROVED and
                app.scheduled_time and
                time_window_start <= app.scheduled_time.astimezone(config.TIMEZONE) <= time_window_end):
            return True, app.id
    return False, None

@router.message(Command("specialist"))
async def cmd_specialist(message: Message, state: FSMContext, session: AsyncSession, bot):
    """Handle the /specialist command to display the specialist's keyboard."""
    telegram_id = message.from_user.id
    crud = CRUD(session)
    user = await crud.get_user(str(telegram_id))
    if not user or user.role != Role.SPECIALIST:
        await message.answer("У вас нет прав специалиста!")
        return
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await message.answer("Специалист не найден. Обратитесь к администратору.")
        return
    try:
        has_appointments, appointment_id = await has_active_appointment(session, specialist.id)
        if has_appointments and appointment_id:
            appointment = await crud.get_appointment(appointment_id)
            scheduled_time = format_appointment_date(appointment.scheduled_time.astimezone(config.TIMEZONE))
            message_text = escape_markdown_v2(
                f"Время заявки \#{appointment.id}! Подтвердите готовность в расписании (время: {scheduled_time})."
            )
            await bot.send_message(
                telegram_id,
                message_text,
                parse_mode="MarkdownV2"
            )
        keyboard = get_specialist_keyboard(has_appointments=has_appointments)
        await message.answer("Панель специалиста:", reply_markup=keyboard)
        await state.clear()
        logger.info(f"Specialist {telegram_id} accessed specialist panel")
    except Exception as e:
        logger.error(f"Failed to fetch specialist appointments for {telegram_id}: {e}", exc_info=True)
        await session.rollback()
        await message.answer("Ошибка при загрузке данных. Попробуйте позже.")

@router.message(F.text == "✅ Закрыть заявку")
async def close_appointment(message: Message, state: FSMContext, session: AsyncSession, bot):
    """Handle the 'Закрыть заявку' button to mark the appointment as COMPLETED, update rank, and request client rating."""
    telegram_id = message.from_user.id
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await message.answer("Специалист не найден.")
        return
    data = await state.get_data()
    appointment_id = data.get("appointment_id")
    if not appointment_id:
        await message.answer("Нет активной заявки для закрытия.")
        return
    appointment = await crud.get_appointment(appointment_id)
    if not appointment or appointment.status != AppointmentStatus.APPROVED:
        await message.answer("Заявка не найдена или уже обработана.")
        await state.clear()
        return
    appointment.status = AppointmentStatus.COMPLETED
    await crud.increment_specialist_completed_appointments(specialist.id)
    new_rank = await crud.update_specialist_rank(specialist.id)
    await session.commit()
    try:
        client_message = escape_markdown_v2(
            f"Заявка #{appointment.id} завершена. Спасибо за консультацию!"
        )
        await bot.send_message(
            appointment.client.user.telegram_id,
            client_message,
            parse_mode="MarkdownV2"
        )
        client_id = appointment.client_id
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="1 ⭐", callback_data=f"rate_{client_id}_1"),
                InlineKeyboardButton(text="2 ⭐", callback_data=f"rate_{client_id}_2"),
                InlineKeyboardButton(text="3 ⭐", callback_data=f"rate_{client_id}_3"),
                InlineKeyboardButton(text="4 ⭐", callback_data=f"rate_{client_id}_4"),
                InlineKeyboardButton(text="5 ⭐", callback_data=f"rate_{client_id}_5"),
            ]
        ])
        response = escape_markdown_v2(f"Заявка #{appointment.id} закрыта. Оцените клиента (ID: {client_id}).")
        if new_rank:
            response += escape_markdown_v2(f"\n\n🎉 Поздравляем! Ваш новый ранг: {new_rank}")
        await message.answer(response, parse_mode="MarkdownV2", reply_markup=markup)
        await state.set_state(SpecialistStates.rating_client)
        await state.update_data(client_id=client_id, appointment_id=appointment_id)
        logger.info(f"Specialist {telegram_id} closed appointment {appointment_id} and requested rating")
        if new_rank:
            logger.info(f"Specialist {telegram_id} promoted to {new_rank}")
    except Exception as e:
        logger.error(f"Failed to notify client or send rating request for appointment {appointment_id}: {e}", exc_info=True)
        await session.rollback()
        await message.answer("Заявка закрыта, но уведомление клиенту или запрос оценки не отправлены.")

@router.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Process the client rating submitted by the specialist."""
    data = callback.data.split("_")
    client_id = int(data[1])
    rating = int(data[2])
    crud = CRUD(session)
    try:
        await crud.update_client_rating(client_id, rating)
        await callback.message.edit_text(f"Спасибо! Клиент (ID: {client_id}) получил {rating} ⭐.")
        specialist = await crud.get_specialist(str(callback.from_user.id))
        has_appointments, new_appointment_id = await has_active_appointment(session, specialist.id)
        keyboard = get_specialist_keyboard(has_appointments=has_appointments)
        await callback.message.answer("Выберите действие:", reply_markup=keyboard)
        logger.info(f"Specialist {callback.from_user.id} rated client {client_id} with {rating}")
    except ValueError as e:
        logger.error(f"Rating error for client {client_id}: {str(e)}")
        await callback.message.edit_text(f"Ошибка: {str(e)}")
        await session.rollback()
    await callback.answer()
    await state.clear()

@router.message(F.text == "❌ Отменить встречу")
async def cancel_appointment(message: Message, state: FSMContext, session: AsyncSession):
    """Handle the 'Отменить встречу' button to prompt for a cancellation reason."""
    telegram_id = message.from_user.id
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await message.answer("Специалист не найден.")
        return
    data = await state.get_data()
    appointment_id = data.get("appointment_id")
    if not appointment_id:
        await message.answer("Нет активной заявки для отмены.")
        return
    appointment = await crud.get_appointment(appointment_id)
    if not appointment or appointment.status != AppointmentStatus.APPROVED:
        await message.answer("Заявка не найдена или уже обработана.")
        await state.clear()
        return
    await message.answer("Введите причину отмены встречи:")
    await state.set_state(SpecialistStates.cancel_reason)
    logger.info(f"Specialist {telegram_id} initiated cancellation for appointment {appointment_id}")

@router.message(SpecialistStates.cancel_reason)
async def process_cancel_reason(message: Message, state: FSMContext, session: AsyncSession, bot):
    """Process the cancellation reason and notify admin and client."""
    reason = message.text.strip()
    if not reason:
        await message.answer("Причина не может быть пустой. Введите снова:")
        return
    data = await state.get_data()
    appointment_id = data.get("appointment_id")
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(message.from_user.id))
    if not specialist:
        await message.answer("Специалист не найден.")
        await state.clear()
        return
    appointment = await crud.get_appointment(appointment_id)
    if not appointment or appointment.status != AppointmentStatus.APPROVED:
        await message.answer("Заявка не найдена или уже обработана.")
        await state.clear()
        return
    appointment.status = AppointmentStatus.CANCELLED
    appointment.reject_reason = f"Отменено специалистом: {reason}"
    await session.commit()
    try:
        admin_message = escape_markdown_v2(
            f"Специалист {specialist.full_name} отменил заявку #{appointment.id}.\n"
            f"Клиент: {appointment.client.full_name}\n"
            f"Причина: {reason}"
        )
        client_message = escape_markdown_v2(
            f"Специалист отменил заявку #{appointment.id}. Свяжитесь с администратором."
        )
        await bot.send_message(config.ADMIN_ID, admin_message, parse_mode="MarkdownV2")
        await bot.send_message(appointment.client.user.telegram_id, client_message, parse_mode="MarkdownV2")
        has_appointments, new_appointment_id = await has_active_appointment(session, specialist.id)
        keyboard = get_specialist_keyboard(has_appointments=has_appointments)
        await message.answer(
            f"Заявка #{appointment.id} отменена.",
            reply_markup=keyboard
        )
        logger.info(f"Specialist {message.from_user.id} cancelled appointment {appointment_id}: {reason}")
    except Exception as e:
        logger.error(f"Failed to notify admin/client for appointment {appointment_id}: {e}", exc_info=True)
        await session.rollback()
        await message.answer("Заявка отменена, но уведомления не отправлены.")
    await state.clear()

async def format_appointments_page(appointments, page: int, specialist_id: int, session: AsyncSession, page_size: int = 5) -> tuple[str, int, int]:
    """Format a page of appointments for display with 'Готов к работе' button for active appointments."""
    start_idx = page * page_size
    end_idx = start_idx + page_size
    total_appointments = len(appointments)
    paginated_appointments = appointments[start_idx:end_idx]
    response = "<b>Ваше расписание:</b>\n\n"
    now = datetime.now(tz=config.TIMEZONE)
    time_window_start = now - timedelta(minutes=15)
    time_window_end = now + timedelta(minutes=15)
    for app in paginated_appointments:
        scheduled_time = format_appointment_date(app.scheduled_time.astimezone(config.TIMEZONE))
        is_active = (
            app.status == AppointmentStatus.APPROVED and
            app.scheduled_time and
            time_window_start <= app.scheduled_time.astimezone(config.TIMEZONE) <= time_window_end
        )
        response += (
            f"Заявка #{app.id}\n"
            f"Клиент: {app.client.full_name}\n"
            f"Время: {scheduled_time}\n"
            f"Причина: {app.reason}\n"
        )
        if is_active and not app.specialist_ready:
            response += f"<b>Статус: Активна (подтвердите готовность)</b>\n\n"
        else:
            response += f"Статус: {app.status.value}\n\n"
    total_pages = (total_appointments + page_size - 1) // page_size
    return response, total_appointments, total_pages

@router.message(F.text == "📅 Расписание")
async def show_schedule(message: Message, state: FSMContext, session: AsyncSession):
    """Display the specialist's schedule with 'Готов к работе' buttons for active appointments."""
    telegram_id = message.from_user.id
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await message.answer("Специалист не найден.")
        return
    try:
        appointments = await crud.get_future_appointments()
        appointments = [app for app in appointments if app.specialist_id == specialist.id]
        if not appointments:
            await message.answer("У вас нет запланированных заявок.")
            return
        page = 0
        response, total_appointments, total_pages = await format_appointments_page(appointments, page, specialist.id, session)
        has_appointments, appointment_id = await has_active_appointment(session, specialist.id)
        keyboard = get_specialist_keyboard(has_appointments=has_appointments)
        pagination_keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for app in appointments[page * 5:(page + 1) * 5]:
            is_active = (
                app.status == AppointmentStatus.APPROVED and
                app.scheduled_time and
                datetime.now(tz=config.TIMEZONE) - timedelta(minutes=15) <= app.scheduled_time.astimezone(config.TIMEZONE) <= datetime.now(tz=config.TIMEZONE) + timedelta(minutes=15)
            )
            if is_active and not app.specialist_ready:
                pagination_keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text=f"Готов к работе (#{app.id})", callback_data=f"specialist_ready_{app.id}")
                ])
        pagination_keyboard.inline_keyboard.extend(get_schedule_pagination_keyboard(page, total_pages).inline_keyboard)
        await message.answer(response, reply_markup=keyboard)
        if pagination_keyboard.inline_keyboard:
            await message.answer("Действия:", reply_markup=pagination_keyboard)
        await state.update_data(schedule_page=page, total_pages=total_pages, appointments=[app.id for app in appointments])
        logger.info(f"Specialist {telegram_id} viewed schedule (page {page + 1}/{total_pages})")
    except Exception as e:
        logger.error(f"Failed to fetch schedule for specialist {telegram_id}: {e}", exc_info=True)
        await session.rollback()
        await message.answer("Ошибка при загрузке расписания. Попробуйте позже.")

@router.callback_query(F.data.startswith("specialist_ready_"))
async def specialist_ready_to_work(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot):
    """Handle specialist's 'Готов к работе' confirmation, notify client without button, and update schedule."""
    telegram_id = callback.from_user.id
    appointment_id = int(callback.data.split("_")[2])
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await callback.message.edit_text("Специалист не найден.")
        await callback.answer()
        return
    appointment = await crud.get_appointment(appointment_id)
    if not appointment or appointment.status != AppointmentStatus.APPROVED or appointment.specialist_ready:
        await callback.message.edit_text("Заявка не найдена, не подтверждена или вы уже подтвердили готовность.")
        await callback.answer()
        return
    appointment.specialist_ready = True
    specialist.is_available = True
    await crud.create_notification_sent(appointment_id, 'specialist_ready')
    await session.commit()
    scheduled_time = format_appointment_date(appointment.scheduled_time.astimezone(config.TIMEZONE))
    client_message = escape_markdown_v2(
        f"Специалист {specialist.full_name} ожидает вас по заявке #{appointment.id} (время: {scheduled_time})."
    )
    specialist_message = escape_markdown_v2(
        f"Вы подтвердили готовность по заявке #{appointment.id} (время: {scheduled_time})."
    )
    try:
        await bot.send_message(
            appointment.client.user.telegram_id,
            client_message,
            parse_mode="MarkdownV2"
        )
        await callback.message.edit_text(
            specialist_message,
            parse_mode="MarkdownV2"
        )
        keyboard = get_specialist_active_keyboard()
        await callback.message.answer(
            f"Вы начали работу по заявке #{appointment.id}. Выберите действие:",
            reply_markup=keyboard
        )
        await state.update_data(appointment_id=appointment_id)
        logger.info(f"Specialist {telegram_id} confirmed readiness for appointment {appointment_id}")
        await callback.answer()
    except Exception as e:
        logger.error(f"Failed to notify client for appointment {appointment_id}: {e}")
        await session.rollback()
        await callback.message.edit_text(
            specialist_message + "\n\nУведомление клиенту не доставлено, но ваша готовность подтверждена.",
            parse_mode="MarkdownV2"
        )
        await callback.answer()

@router.callback_query(F.data.startswith("schedule_next"))
async def schedule_next(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle the 'Next' button to show the next page of appointments."""
    telegram_id = callback.from_user.id
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await callback.message.edit_text("Специалист не найден.")
        await callback.answer()
        return
    data = await state.get_data()
    page = data.get("schedule_page", 0)
    total_pages = data.get("total_pages", 1)
    appointment_ids = data.get("appointments", [])
    if page + 1 >= total_pages:
        await callback.answer("Это последняя страница.")
        return
    try:
        appointments = await crud.get_future_appointments()
        appointments = [app for app in appointments if app.specialist_id == specialist.id and app.id in appointment_ids]
        page += 1
        response, total_appointments, total_pages = await format_appointments_page(appointments, page, specialist.id, session)
        has_appointments, appointment_id = await has_active_appointment(session, specialist.id)
        keyboard = get_specialist_keyboard(has_appointments=has_appointments)
        pagination_keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for app in appointments[page * 5:(page + 1) * 5]:
            is_active = (
                app.status == AppointmentStatus.APPROVED and
                app.scheduled_time and
                datetime.now(tz=config.TIMEZONE) - timedelta(minutes=15) <= app.scheduled_time.astimezone(config.TIMEZONE) <= datetime.now(tz=config.TIMEZONE) + timedelta(minutes=15)
            )
            if is_active and not app.specialist_ready:
                pagination_keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text=f"Готов к работе (#{app.id})", callback_data=f"specialist_ready_{app.id}")
                ])
        pagination_keyboard.inline_keyboard.extend(get_schedule_pagination_keyboard(page, total_pages).inline_keyboard)
        await callback.message.edit_text(response, reply_markup=pagination_keyboard)
        await callback.message.answer("Выберите действие:", reply_markup=keyboard)
        await state.update_data(schedule_page=page, total_pages=total_pages)
        logger.info(f"Specialist {telegram_id} viewed schedule (page {page + 1}/{total_pages})")
    except Exception as e:
        logger.error(f"Failed to fetch next schedule page for specialist {telegram_id}: {e}", exc_info=True)
        await session.rollback()
        await callback.message.edit_text("Ошибка при загрузке расписания. Попробуйте позже.")
    await callback.answer()

@router.callback_query(F.data.startswith("schedule_prev"))
async def schedule_prev(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Handle the 'Previous' button to show the previous page of appointments."""
    telegram_id = callback.from_user.id
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await callback.message.edit_text("Специалист не найден.")
        await callback.answer()
        return
    data = await state.get_data()
    page = data.get("schedule_page", 0)
    total_pages = data.get("total_pages", 1)
    appointment_ids = data.get("appointments", [])
    if page <= 0:
        await callback.answer("Это первая страница.")
        return
    try:
        appointments = await crud.get_future_appointments()
        appointments = [app for app in appointments if app.specialist_id == specialist.id and app.id in appointment_ids]
        page -= 1
        response, total_appointments, total_pages = await format_appointments_page(appointments, page, specialist.id, session)
        has_appointments, appointment_id = await has_active_appointment(session, specialist.id)
        keyboard = get_specialist_keyboard(has_appointments=has_appointments)
        pagination_keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        for app in appointments[page * 5:(page + 1) * 5]:
            is_active = (
                app.status == AppointmentStatus.APPROVED and
                app.scheduled_time and
                datetime.now(tz=config.TIMEZONE) - timedelta(minutes=15) <= app.scheduled_time.astimezone(config.TIMEZONE) <= datetime.now(tz=config.TIMEZONE) + timedelta(minutes=15)
            )
            if is_active and not app.specialist_ready:
                pagination_keyboard.inline_keyboard.append([
                    InlineKeyboardButton(text=f"Готов к работе (#{app.id})", callback_data=f"specialist_ready_{app.id}")
                ])
        pagination_keyboard.inline_keyboard.extend(get_schedule_pagination_keyboard(page, total_pages).inline_keyboard)
        await callback.message.edit_text(response, reply_markup=pagination_keyboard)
        await callback.message.answer("Выберите действие:", reply_markup=keyboard)
        await state.update_data(schedule_page=page, total_pages=total_pages)
        logger.info(f"Specialist {telegram_id} viewed schedule (page {page + 1}/{total_pages})")
    except Exception as e:
        logger.error(f"Failed to fetch previous schedule page for specialist {telegram_id}: {e}", exc_info=True)
        await session.rollback()
        await callback.message.edit_text("Ошибка при загрузке расписания. Попробуйте позже.")
    await callback.answer()

@router.message(F.text == "📊 Отчеты")
async def show_reports(message: Message, session: AsyncSession):
    """Display options for selecting the report period."""
    telegram_id = message.from_user.id
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await message.answer("Специалист не найден.")
        return
    keyboard = get_report_period_keyboard()
    await message.answer("Выберите период для отчета:", reply_markup=keyboard)
    logger.info(f"Specialist {telegram_id} requested reports")

@router.message(F.text == "📈 Мой ранг")
async def show_rank(message: Message, session: AsyncSession):
    """Display the specialist's current military rank and completed appointments."""
    telegram_id = message.from_user.id
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await message.answer("Специалист не найден.")
        return
    try:
        ranks = [
            "Подстаканник для кофе", "Шлепок майонезный", "Куркума волосатая", "Капрал", "Старший Капрал",
            "Боевая капибара", "Слон", "Рядовой", "Ефрейтор", "Сержант", "Дембель"
        ]
        current_rank_index = min(specialist.completed_appointments // 7, len(ranks) - 1)
        next_rank = ranks[current_rank_index + 1] if current_rank_index < len(ranks) - 1 else "Максимальный ранг"
        progress = 7 - (specialist.completed_appointments % 7) if specialist.completed_appointments < 70 else 0
        response = escape_markdown_v2(
            f"<b>Ваш военный ранг</b>\n\n"
            f"Ранг: {specialist.rank}\n"
            f"Завершено заявок: {specialist.completed_appointments}\n"
            f"До следующего ранга ({next_rank}): {progress} заявок"
        )
        has_appointments, _ = await has_active_appointment(session, specialist.id)
        keyboard = get_specialist_keyboard(has_appointments=has_appointments)
        await message.answer(response, parse_mode="MarkdownV2", reply_markup=keyboard)
        logger.info(f"Specialist {telegram_id} viewed rank")
    except Exception as e:
        logger.error(f"Failed to fetch rank for specialist {telegram_id}: {e}", exc_info=True)
        await session.rollback()
        await message.answer("Ошибка при загрузке ранга. Попробуйте позже.")

@router.callback_query(F.data.startswith("report_period:"))
async def process_report_period(callback: CallbackQuery, session: AsyncSession):
    """Generate and display the report for the selected period."""
    telegram_id = callback.from_user.id
    period = callback.data.split(":")[1]
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await callback.message.edit_text("Специалист не найден.")
        await callback.answer()
        return
    now = datetime.now(tz=config.TIMEZONE)
    if period == "week":
        start_date = now - timedelta(days=7)
        period_label = "за последнюю неделю"
    elif period == "month":
        start_date = now - timedelta(days=30)
        period_label = "за последний месяц"
    else:  # 3months
        start_date = now - timedelta(days=90)
        period_label = "за последние 3 месяца"
    try:
        appointments = await crud.get_appointments_by_specialist(specialist.id)
        completed_count = 0
        canceled_count = 0
        for app in appointments:
            if app.scheduled_time and start_date <= app.scheduled_time.astimezone(config.TIMEZONE) <= now:
                if app.status == AppointmentStatus.COMPLETED:
                    completed_count += 1
                elif app.status == AppointmentStatus.CANCELLED:
                    canceled_count += 1
        response = escape_markdown_v2(
            f"<b>Отчет {period_label}</b>\n\n"
            f"Выполнено заявок: {completed_count}\n"
            f"Отменено заявок: {canceled_count}"
        )
        has_appointments, _ = await has_active_appointment(session, specialist.id)
        keyboard = get_specialist_keyboard(has_appointments=has_appointments)
        await callback.message.edit_text(response, parse_mode="MarkdownV2")
        await callback.message.answer("Выберите действие:", reply_markup=keyboard)
        logger.info(f"Specialist {telegram_id} generated report for {period}")
    except Exception as e:
        logger.error(f"Failed to generate report for specialist {telegram_id}: {e}", exc_info=True)
        await session.rollback()
        await callback.message.edit_text("Ошибка при формировании отчета. Попробуйте позже.")
    await callback.answer()

@router.message(F.text == "🔄 Изменить доступность")
async def toggle_availability(message: Message, state: FSMContext, session: AsyncSession):
    """Start the process of changing the specialist's availability status."""
    telegram_id = message.from_user.id
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await message.answer("Специалист не найден.")
        return
    await message.answer(
        "Выберите новый статус:\n1. Доступен\n2. Недоступен",
        reply_markup=None
    )
    await state.set_state(SpecialistStates.change_availability)
    logger.info(f"Specialist {telegram_id} started changing availability")

@router.message(SpecialistStates.change_availability, F.text.in_(["1", "2"]))
async def process_availability(message: Message, state: FSMContext, session: AsyncSession):
    """Process the availability status selection."""
    telegram_id = message.from_user.id
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await message.answer("Специалист не найден.")
        await state.clear()
        return
    is_available = message.text == "1"
    await crud.update_specialist_availability(specialist.id, is_available)
    status_text = "доступен" if is_available else "недоступен"
    has_appointments, _ = await has_active_appointment(session, specialist.id)
    keyboard = get_specialist_keyboard(has_appointments=has_appointments)
    await message.answer(
        f"Ваш статус изменен: {status_text}.",
        reply_markup=keyboard
    )
    logger.info(f"Specialist {telegram_id} changed availability to {status_text}")
    await state.clear()

@router.message(SpecialistStates.change_availability)
async def invalid_availability(message: Message):
    """Handle invalid input during availability change."""
    telegram_id = message.from_user.id
    await message.answer("Пожалуйста, выберите 1 (Доступен) или 2 (Недоступен).")
    logger.warning(f"Specialist {telegram_id} provided invalid availability input: {message.text}")

@router.message(F.text == "📝 Отправить отчет")
async def start_report_submission(message: Message, state: FSMContext, session: AsyncSession):
    """Start the process of submitting a report by the specialist."""
    telegram_id = message.from_user.id
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await message.answer("Специалист не найден.")
        return
    appointments = await crud.get_appointments_by_specialist(specialist.id)
    if not appointments:
        await message.answer("У вас нет активных заявок для отчетов.")
        return
    await message.answer(
        "Введите текст отчета (например, описание выполненной работы):",
        reply_markup=None
    )
    await state.set_state(SpecialistStates.submit_report_text)
    logger.info(f"Specialist {telegram_id} started report submission")

@router.message(SpecialistStates.submit_report_text)
async def process_report_text(message: Message, state: FSMContext, session: AsyncSession, bot):
    """Process the report text and save it."""
    telegram_id = message.from_user.id
    crud = CRUD(session)
    specialist = await crud.get_specialist(str(telegram_id))
    if not specialist:
        await message.answer("Специалист не найден.")
        await state.clear()
        return
    report_text = message.text.strip()
    if len(report_text) < 10:
        await message.answer("Отчет слишком короткий. Введите минимум 10 символов.")
        return
    try:
        await crud.create_specialist_report(specialist.id, report_text)
        report_message = escape_markdown_v2(
            f"Специалист {specialist.full_name} отправил отчет:\n{report_text}"
        )
        await bot.send_message(config.ADMIN_ID, report_message, parse_mode="MarkdownV2")
        has_appointments, _ = await has_active_appointment(session, specialist.id)
        keyboard = get_specialist_keyboard(has_appointments=has_appointments)
        await message.answer(
            "Отчет успешно отправлен.",
            reply_markup=keyboard
        )
        logger.info(f"Specialist {telegram_id} submitted report: {report_text[:50]}...")
    except Exception as e:
        logger.error(f"Failed to save or notify admin for report by specialist {telegram_id}: {e}", exc_info=True)
        await session.rollback()
        await message.answer("Ошибка при отправке отчета. Попробуйте позже.")
    await state.clear()