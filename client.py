from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

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
            await y_markup=get_client_keyboard())
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
async def process
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

@router.callback_quer

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
            f"Ст
    await message.answer("Выберите заявку для отмены:", reply_markup=keyboard)
    await state.set_state(ClientStates.cancel_appointment)

@router.callback_query(
    if appointment.specialist:
        specialist_message = escape_markdown_v2(
            f"Клиент {appointment.client.full_name} отменил заявку #{appointment.id}.\nПричина: {reason}"
        )
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
            ap
        return
    appointment.client_ready = True  # Set client_ready instead of status
    await session.commit()
    scheduled_time = format_appointment_date(appointment.scheduled_time)
    username = appointment.specialist.username
    phone = getattr(appoent {appointment_id}: {e}")
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
        await callback
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
            
    response = (
        f"<b>Ваш рейтинг</b>\n\n"
        f"Средний рейтинг: {avg_rating:.1f}\n"
        f"Количество оценок: {client.rating_count}"
    )
    await message.answer(response, reply_markup=get_client_keyboard())
    logger.info(f"Client {telegram_id} viewed rating")
