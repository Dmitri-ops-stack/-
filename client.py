from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Client, Role, Appointment, AppointmentStatus, Blacklist
from database.crud import CRUD
from config import config
from keyboards import get_client_keyboard
from utils.states import ClientStates
from utils.helpers import validate_phone, validate_date, format_appointment_date
import logging
from datetime import datetime

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

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id
    crud = CRUD(session)
    await state.clear()
    logger.info(f"Processing /start for telegram_id={telegram_id}")
    if telegram_id == config.ADMIN_ID:
        user = await crud.get_user(str(telegram_id))
        if user:
            if user.role != Role.ADMIN:
                user.role = Role.ADMIN
                await session.commit()
                logger.info(f"Updated role to ADMIN for telegram_id={telegram_id}")
        else:
            user = User(telegram_id=str(telegram_id), role=Role.ADMIN)
            session.add(user)
            await session.commit()
            logger.info(f"Created admin with telegram_id={telegram_id}")
        await message.answer("Добро пожаловать, администратор! Используйте /admin для управления.")
        return
    user = await crud.get_user(str(telegram_id))
    if user:
        if user.role == Role.CLIENT:
            await message.answer("Вы уже зарегистрированы как клиент!\nВыберите действие:", reply_markup=get_client_keyboard())
        elif user.role == Role.SPECIALIST:
            await message.answer("Вы уже зарегистрированы как специалист!\nИспользуйте /specialist для работы.")
        elif user.role == Role.ADMIN:
            await message.answer("Вы уже зарегистрированы как администратор!\nИспользуйте /admin для управления.")
        return
    blacklist_entry = await crud.is_blacklisted(str(telegram_id))
    if blacklist_entry and blacklist_entry.blocked_until > datetime.now(tz=config.TIMEZONE):
        await message.answer(f"🚫 Вы в черном списке до {blacklist_entry.blocked_until.astimezone(config.TIMEZONE).strftime('%d.%m.%Y %H:%M')}!")
        return
    elif blacklist_entry:
        await session.delete(blacklist_entry)
        await session.commit()
    await message.answer("Добро пожаловать! Введите кодовое слово:")
    await state.set_state(ClientStates.await_codeword)

@router.message(ClientStates.await_codeword)
async def process_codeword(message: Message, state: FSMContext, session: AsyncSession):
    if message.text != config.CODE_WORD:
        await message.answer("❌ Неверное кодовое слово!")
        return
    telegram_id = message.from_user.id
    crud = CRUD(session)
    user = await crud.get_user(str(telegram_id))
    if user:
        if user.role == Role.CLIENT:
            await message.answer("Вы уже зарегистрированы как клиент!\nВыберите действие:", reply_markup=get_client_keyboard())
            await state.clear()
            return
        elif user.role == Role.SPECIALIST:
            await message.answer("Вы специалист! Используйте /specialist.")
            await state.clear()
            return
        elif user.role == Role.ADMIN:
            await message.answer("Вы администратор! Используйте /admin.")
            await state.clear()
            return
    user = User(telegram_id=str(telegram_id), role=Role.CLIENT)
    await crud.create_user(user.telegram_id, user.role)
    await message.answer("Введите ваше полное имя:")
    await state.set_state(ClientStates.registration)

@router.message(ClientStates.registration)
async def process_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()
    if not full_name:
        await message.answer("Имя не может быть пустым. Введите снова:")
        return
    await state.update_data(full_name=full_name)
    await message.answer("Введите ваш город:")
    await state.set_state(ClientStates.city)

@router.message(ClientStates.city)
async def process_city(message: Message, state: FSMContext):
    city = message.text.strip()
    if not city:
        await message.answer("Город не может быть пустым. Введите снова:")
        return
    await state.update_data(city=city)
    await message.answer("Введите номер телефона (11 цифр, например, 89991234567):")
    await state.set_state(ClientStates.phone)

@router.message(ClientStates.phone)
async def process_phone(message: Message, state: FSMContext, session: AsyncSession):
    phone = message.text.strip()
    if not validate_phone(phone):
        await message.answer("Номер телефона должен состоять из 11 цифр (например, 89991234567). Попробуйте снова:")
        return
    data = await state.get_data()
    telegram_id = message.from_user.id
    crud = CRUD(session)
    try:
        client = Client(
            user_id=str(telegram_id),
            full_name=data["full_name"],
            city=data["city"],
            phone=phone
        )
        await crud.create_client(client)
        await message.answer("✅ Регистрация завершена!", reply_markup=get_client_keyboard())
        await state.clear()
    except Exception as e:
        logger.error(f"Failed to create client {telegram_id}: {e}")
        await session.rollback()
        await message.answer("Ошибка при регистрации. Попробуйте позже.")
        return

@router.message(F.text == "📝 Новая заявка")
async def new_appointment(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Р", callback_data="inspection_type:R")],
        [InlineKeyboardButton(text="СТР", callback_data="inspection_type:STR")],
        [InlineKeyboardButton(text="Б", callback_data="inspection_type:B")]
    ])
    await message.answer("Выберите подразделение:", reply_markup=keyboard)
    await state.set_state(ClientStates.choose_type)

@router.callback_query(F.data.startswith("inspection_type:"))
async def process_inspection_type(callback: CallbackQuery, state: FSMContext):
    inspection_type = callback.data.split(":")[1]
    await state.update_data(inspection_type=inspection_type)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Активное", callback_data="body_part:active")],
        [InlineKeyboardButton(text="Пассивное", callback_data="body_part:passive")]
    ])
    await callback.message.edit_text("Выберите тип изделия:", reply_markup=keyboard)
    await state.set_state(ClientStates.choose_part)

@router.callback_query(F.data.startswith("body_part:"))
async def process_body_part(callback: CallbackQuery, state: FSMContext):
    body_part = callback.data.split(":")[1]
    await state.update_data(body_part=body_part)
    if body_part == "active":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="МоМ", callback_data="complex:Эко-М")],
            [InlineKeyboardButton(text="Мод(01,02,07)", callback_data="complex:Модуль")],
            [InlineKeyboardButton(text="РК01", callback_data="complex:РК-01")],
            [InlineKeyboardButton(text="ЭкоН", callback_data="complex:ЭкоН")]
        ])
        await callback.message.edit_text("Выберите комплекс:", reply_markup=keyboard)
        await state.set_state(ClientStates.choose_complex)
    else:
        await callback.message.edit_text("Введите дату записи (в формате ДД.ММ.ГГГГ):", reply_markup=None)
        await state.set_state(ClientStates.enter_date)

@router.callback_query(F.data.startswith("complex:"))
async def process_complex(callback: CallbackQuery, state: FSMContext):
    complex = callback.data.split(":")[1]
    await state.update_data(complex=complex)
    await callback.message.edit_text("Введите дату (в формате ДД.ММ.ГГГГ):", reply_markup=None)
    await state.set_state(ClientStates.enter_date)

@router.message(ClientStates.enter_date)
async def process_date(message: Message, state: FSMContext):
    date_str = message.text.strip()
    try:
        if not validate_date(date_str):
            await message.answer("Неверный формат или дата в прошлом/выходной. Введите в формате ДД.ММ.ГГГГ (например, 20.04.2025):")
            return
        proposed_date = datetime.strptime(date_str, "%d.%m.%Y").replace(tzinfo=config.TIMEZONE)
        await state.update_data(proposed_date=proposed_date)
        await message.answer("Опишите проблему:")
        await state.set_state(ClientStates.collecting_reason)
    except ValueError as e:
        await message.answer(f"Ошибка: {str(e)}. Введите дату в формате ДД.ММ.ГГГГ (например, 20.04.2025), только рабочие дни (пн-пт):")
        return

@router.message(ClientStates.collecting_reason)
async def process_collecting_reason(message: Message, state: FSMContext, session: AsyncSession, bot):
    data = await state.get_data()
    telegram_id = message.from_user.id
    crud = CRUD(session)
    client = await crud.get_client(str(telegram_id))
    if not client:
        await message.answer("Ошибка: клиент не найден. Пройдите регистрацию заново.")
        await state.clear()
        return
    if "proposed_date" not in data:
        logger.warning(f"proposed_date missing for client {telegram_id}. Prompting for date.")
        await message.answer("Дата не указана. Введите дату (в формате ДД.ММ.ГГГГ):")
        await state.set_state(ClientStates.enter_date)
        return
    description = (
        f"подразделение: {data.get('inspection_type', '-')}\n"
        f"Часть: {data.get('body_part', '-')}\n"
        f"Комплекс: {data.get('complex', '-')}\n"
        f"Дата: {data['proposed_date'].strftime('%d.%m.%Y')}\n"
        f"Причина: {message.text}"
    )
    try:
        appointment = Appointment(
            client_id=client.id,
            proposed_date=data["proposed_date"],
            complex=data.get("complex", "-"),
            reason=description,
            status=AppointmentStatus.PENDING
        )
        await crud.create_appointment(appointment)
        avg_rating = (client.rating / client.rating_count) if client.rating_count > 0 else 0
        admin_message = escape_markdown_v2(
            f"Новая заявка #{appointment.id} от {client.full_name} (ср. рейтинг: {avg_rating:.1f}):\n{description}"
        )
        await bot.send_message(
            config.ADMIN_ID,
            admin_message,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{appointment.id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{appointment.id}")]
            ])
        )
        await message.answer("✅ Заявка создана!", reply_markup=get_client_keyboard())
        await state.clear()
    except Exception as e:
        logger.error(f"Failed to create appointment for client {telegram_id}: {e}")
        await session.rollback()
        await message.answer("Ошибка при создании заявки. Попробуйте позже.")
        return

@router.message(F.text == "📋 Мои заявки")
async def my_appointments(message: Message, session: AsyncSession):
    telegram_id = message.from_user.id
    crud = CRUD(session)
    client = await crud.get_client(str(telegram_id))
    if not client:
        await message.answer("Ошибка: клиент не найден. Пройдите регистрацию заново.")
        return
    appointments = await crud.get_appointments_by_client(client.id)
    if not appointments:
        await message.answer("У вас нет заявок.")
        return
    response = "<b>Ваши заявки:</b>\n\n"
    for app in appointments:
        status = app.status.value
        date = format_appointment_date(app.proposed_date)
        scheduled_time = app.scheduled_time.astimezone(config.TIMEZONE).strftime("%H:%M") if app.scheduled_time else "Не назначено"
        specialist = app.specialist.full_name if app.specialist else "Не назначен"
        response += (
            f"Заявка #{app.id}\n"
            f"Дата: {date}\n"
            f"Время: {scheduled_time}\n"
            f"Специалист: {specialist}\n"
            f"Статус: {status}\n"
            f"Причина: {app.reason}\n\n"
        )
    await message.answer(response, reply_markup=get_client_keyboard())

@router.message(F.text == "🚫 Отменить заявку")
async def cancel_appointment(message: Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id
    crud = CRUD(session)
    client = await crud.get_client(str(telegram_id))
    if not client:
        await message.answer("Ошибка: клиент не найден. Пройдите регистрацию заново.")
        await state.clear()
        return
    appointments = await crud.get_appointments_by_client(client.id)
    active_appointments = [app for app in appointments if app.status in [AppointmentStatus.PENDING, AppointmentStatus.APPROVED]]
    if not active_appointments:
        await message.answer("У вас нет активных заявок для отмены.", reply_markup=get_client_keyboard())
        await state.clear()
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Заявка #{app.id} ({format_appointment_date(app.proposed_date)})", callback_data=f"cancel_app_{app.id}")]
        for app in active_appointments
    ])
    await message.answer("Выберите заявку для отмены:", reply_markup=keyboard)
    await state.set_state(ClientStates.cancel_appointment)

@router.callback_query(F.data.startswith("cancel_app_"), ClientStates.cancel_appointment)
async def process_cancel_appointment(callback: CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split("_")[2])
    await state.update_data(appointment_id=appointment_id)
    await callback.message.edit_text("Укажите причину отмены:")
    await state.set_state(ClientStates.cancel_reason)

@router.message(ClientStates.cancel_reason)
async def process_cancel_reason(message: Message, state: FSMContext, session: AsyncSession, bot):
    reason = message.text.strip()
    data = await state.get_data()
    appointment_id = data.get("appointment_id")
    crud = CRUD(session)
    appointment = await crud.get_appointment(appointment_id)
    if not appointment:
        await message.answer("Заявка не найдена.", reply_markup=get_client_keyboard())
        await state.clear()
        return
    appointment.status = AppointmentStatus.CANCELED
    appointment.reason = f"Отменено клиентом: {reason}\n{appointment.reason}"
    await session.commit()
    admin_message = escape_markdown_v2(
        f"Клиент {appointment.client.full_name} отменил заявку #{appointment.id}.\nПричина: {reason}"
    )
    await bot.send_message(config.ADMIN_ID, admin_message, parse_mode="MarkdownV2")
    if appointment.specialist:
        specialist_message = escape_markdown_v2(
            f"Клиент {appointment.client.full_name} отменил заявку #{appointment.id}.\nПричина: {reason}"
        )
        await bot.send_message(appointment.specialist.user_id, specialist_message, parse_mode="MarkdownV2")
    await message.answer("Заявка успешно отменена.", reply_markup=get_client_keyboard())
    await state.clear()

async def notify_client_appointment_approved(appointment: Appointment, bot):
    """
    Notify the client that their appointment is approved, including specialist's phone number (if available) and a username-based Telegram link.
    """
    scheduled_time = format_appointment_date(appointment.scheduled_time)
    username = appointment.specialist.username
    phone = getattr(appointment.specialist, 'phone', None)
    phone_display = escape_markdown_v2(f"Телефон специалиста: {phone}") if phone and phone.strip() else "Телефон специалиста: не указан"
    if username and username.strip():
        if not username.startswith('@'):
            username = f"@{username}"
        specialist_link = f"https://t.me/{username}"
        specialist_contact = f"[Связаться со специалистом]({specialist_link})"
    else:
        specialist_link = f"https://t.me/{config.ADMIN_ID}"
        specialist_contact = f"[Связаться с администратором]({specialist_link})"
        logger.warning(f"Specialist {appointment.specialist.full_name} (ID: {appointment.specialist.user_id}, appointment_id: {appointment.id}) has no valid username. Using admin link.")
    message_lines = [
        escape_markdown_v2(f"Ваша заявка #{appointment.id} подтверждена!"),
        escape_markdown_v2(f"Дата и время: {scheduled_time}"),
        escape_markdown_v2(f"Специалист: {appointment.specialist.full_name}"),
        phone_display,
        specialist_contact
    ]
    if not username or not username.strip():
        message_lines.append(f"Если не можете связаться со специалистом, обратитесь к администратору: [Администратор](https://t.me/{config.ADMIN_ID})")
    try:
        await bot.send_message(
            appointment.client.user.telegram_id,
            "\n".join(message_lines),
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"client_approve_{appointment.id}")],
                [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"client_decline_{appointment.id}")]
            ])
        )
        logger.info(f"Notified client {appointment.client.user.telegram_id} about approved appointment {appointment.id}")
    except Exception as e:
        logger.error(f"Failed to notify client {appointment.client.user.telegram_id} for appointment {appointment.id}: {e}")
        admin_message = escape_markdown_v2(
            f"Ошибка: Не удалось уведомить клиента {appointment.client.full_name} о подтверждении заявки #{appointment.id}."
        )
        await bot.send_message(config.ADMIN_ID, admin_message, parse_mode="MarkdownV2")

@router.callback_query(F.data.startswith("client_approve_"))
async def client_approve_appointment(callback: CallbackQuery, session: AsyncSession):
    """
    Handle client's approval of an appointment, retaining specialist details.
    """
    appointment_id = int(callback.data.split("_")[2])
    crud = CRUD(session)
    appointment = await crud.get_appointment(appointment_id)
    if not appointment:
        await callback.message.edit_text("Заявка не найдена.")
        return
    appointment.client_ready = True  # Set client_ready instead of status
    await session.commit()
    scheduled_time = format_appointment_date(appointment.scheduled_time)
    username = appointment.specialist.username
    phone = getattr(appointment.specialist, 'phone', None)
    phone_display = escape_markdown_v2(f"Телефон специалиста: {phone}") if phone and phone.strip() else "Телефон специалиста: не указан"
    if username and username.strip():
        if not username.startswith('@'):
            username = f"@{username}"
        specialist_link = f"https://t.me/{username}"
        specialist_contact = f"[Связаться со специалистом]({specialist_link})"
    else:
        specialist_link = f"https://t.me/{config.ADMIN_ID}"
        specialist_contact = f"[Связаться с администратором]({specialist_link})"
        logger.warning(f"Specialist {appointment.specialist.full_name} (ID: {appointment.specialist.user_id}, appointment_id: {appointment_id}) has no valid username. Using admin link.")
    message_lines = [
        escape_markdown_v2(f"Заявка #{appointment.id} одобрена! Ожидайте встречи."),
        escape_markdown_v2(f"Дата и время: {scheduled_time}"),
        escape_markdown_v2(f"Специалист: {appointment.specialist.full_name}"),
        phone_display,
        specialist_contact
    ]
    if not username or not username.strip():
        message_lines.append(f"Если не можете связаться со специалистом, обратитесь к администратору: [Администратор](https://t.me/{config.ADMIN_ID})")
    try:
        await callback.message.edit_text(
            "\n".join(message_lines),
            parse_mode="MarkdownV2"
        )
        logger.info(f"Client {appointment.client.user.telegram_id} approved appointment {appointment_id}")
    except Exception as e:
        logger.error(f"Failed to update approval message for client {appointment.client.user.telegram_id}, appointment {appointment_id}: {e}")
        await callback.message.edit_text("Ошибка при обновлении сообщения. Заявка одобрена.")

@router.callback_query(F.data.startswith("client_decline_"))
async def client_decline_appointment(callback: CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split("_")[2])
    await state.update_data(appointment_id=appointment_id, action="decline")
    await callback.message.edit_text("Опишите причину отказа:")
    await state.set_state(ClientStates.reject_reason)

@router.callback_query(F.data.startswith("client_refuse_"))
async def client_refuse_appointment(callback: CallbackQuery, state: FSMContext):
    appointment_id = int(callback.data.split("_")[2])
    await state.update_data(appointment_id=appointment_id, action="refuse")
    await callback.message.edit_text("Опишите причину отказа:")
    await state.set_state(ClientStates.reject_reason)

@router.message(ClientStates.reject_reason)
async def process_reject_reason(message: Message, state: FSMContext, session: AsyncSession, bot):
    data = await state.get_data()
    appointment_id = data["appointment_id"]
    action = data.get("action")
    crud = CRUD(session)
    appointment = await crud.get_appointment(appointment_id)
    if not appointment:
        await message.answer("Заявка не найдена.", reply_markup=get_client_keyboard())
        await state.clear()
        return
    reason = escape_markdown_v2(message.text)
    if action == "decline":
        appointment.status = AppointmentStatus.PENDING  # Revert to PENDING for admin review
        appointment.reject_reason = reason
        await session.commit()
        admin_message = escape_markdown_v2(
            f"Клиент {appointment.client.full_name} отклонил заявку #{appointment.id}.\nПричина: {reason}"
        )
        await bot.send_message(
            config.ADMIN_ID,
            admin_message,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{appointment.id}")],
                [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_{appointment.id}")]
            ])
        )
        await message.answer("Выберите новую дату (в формате ДД.ММ.ГГГГ):")
        await state.set_state(ClientStates.enter_date)
    elif action == "refuse":
        appointment.status = AppointmentStatus.CANCELED
        appointment.reject_reason = reason
        await session.commit()
        admin_message = escape_markdown_v2(
            f"Клиент {appointment.client.full_name} отказался от заявки #{appointment.id}.\nПричина: {reason}"
        )
        await bot.send_message(config.ADMIN_ID, admin_message, parse_mode="MarkdownV2")
        if appointment.specialist:
            specialist_message = escape_markdown_v2(
                f"Клиент {appointment.client.full_name} отказался от заявки #{appointment.id}.\nПричина: {reason}"
            )
            await bot.send_message(appointment.specialist.user_id, specialist_message, parse_mode="MarkdownV2")
        await message.answer("Заявка отменена.", reply_markup=get_client_keyboard())
        await state.clear()

@router.callback_query(F.data.startswith("client_ready_"))
async def client_ready_to_work(callback: CallbackQuery, session: AsyncSession, bot):
    """
    Handle client's 'Готов к работе' confirmation, notify specialist without button, and update client's message.
    """
    appointment_id = int(callback.data.split("_")[2])
    crud = CRUD(session)
    appointment = await crud.get_appointment(appointment_id)
    if not appointment or appointment.status != AppointmentStatus.APPROVED or appointment.client_ready:
        await callback.message.edit_text("Заявка не найдена, не подтверждена или вы уже подтвердили готовность.")
        await callback.answer()
        return
    appointment.client_ready = True
    await session.commit()
    scheduled_time = format_appointment_date(appointment.scheduled_time)
    username = appointment.specialist.username
    phone = getattr(appointment.specialist, 'phone', None)
    phone_display = escape_markdown_v2(f"Телефон специалиста: {phone}") if phone and phone.strip() else "Телефон специалиста: не указан"
    if username and username.strip():
        if not username.startswith('@'):
            username = f"@{username}"
        specialist_link = f"https://t.me/{username}"
        specialist_contact = f"[Связаться со специалистом]({specialist_link})"
    else:
        specialist_link = f"https://t.me/{config.ADMIN_ID}"
        specialist_contact = f"[Связаться с администратором]({specialist_link})"
        logger.warning(f"Specialist {appointment.specialist.full_name} (ID: {appointment.specialist.user_id}, appointment_id: {appointment_id}) has no valid username. Using admin link.")
    client_message_lines = [
        escape_markdown_v2(f"Вы подтвердили готовность по заявке #{appointment.id}. Ожидайте специалиста."),
        escape_markdown_v2(f"Дата и время: {scheduled_time}"),
        escape_markdown_v2(f"Специалист: {appointment.specialist.full_name}"),
        phone_display,
        specialist_contact
    ]
    if not username or not username.strip():
        client_message_lines.append(f"Если не можете связаться со специалистом, обратитесь к администратору: [Администратор](https://t.me/{config.ADMIN_ID})")
    specialist_message = escape_markdown_v2(
        f"Клиент {appointment.client.full_name} ожидает вас по заявке #{appointment.id} (время: {scheduled_time})."
    )
    try:
        await bot.send_message(
            appointment.specialist.user_id,
            specialist_message,
            parse_mode="MarkdownV2"
        )
        await callback.message.edit_text(
            "\n".join(client_message_lines),
            parse_mode="MarkdownV2"
        )
        logger.info(f"Client {appointment.client.user.telegram_id} confirmed readiness for appointment {appointment_id}")
        await callback.answer()
    except Exception as e:
        logger.error(f"Failed to notify specialist for appointment {appointment_id}: {e}")
        await session.rollback()
        await callback.message.edit_text(
            "\n".join(client_message_lines + ["Уведомление специалисту не доставлено, но ваша готовность подтверждена."]),
            parse_mode="MarkdownV2"
        )
        await callback.answer()

@router.message(F.text == "📈 Мой рейтинг")
async def show_rating(message: Message, session: AsyncSession):
    telegram_id = message.from_user.id
    crud = CRUD(session)
    client = await crud.get_client(str(telegram_id))
    if not client:
        await message.answer("Ошибка: клиент не найден. Пройдите регистрацию заново.")
        return
    avg_rating = (client.rating / client.rating_count) if client.rating_count > 0 else 0
    response = (
        f"<b>Ваш рейтинг</b>\n\n"
        f"Средний рейтинг: {avg_rating:.1f}\n"
        f"Количество оценок: {client.rating_count}"
    )
    await message.answer(response, reply_markup=get_client_keyboard())
    logger.info(f"Client {telegram_id} viewed rating")