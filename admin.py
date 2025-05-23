from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from database.
    crud = CRUD(session)
    user = await crud.get_user(str(telegram_id))
    if not user or user.role != Role.ADMIN:
        await message.answer("У вас нет прав администратора!")
        return
    await message.answer("Панель администратора:", reply_markup=get_admin_keyboard())

@router.message(F.text == "📊 Статистика")
async def show_statistics(message: Message, session: AsyncSession):
    telegram_id = message.from_user.id
    crud = CRUD(session)
    user = await crud.get_user(str(telegram_id))
    if not user or user.role != Role.ADMIN:
        await message.answer("У вас нет прав администратора!")
        return
    )
    for spec in specialists:
        response += (
            f"Специалист: {spec.full_name}\n"
            f"Выполнено заявок: {spec.completed_appointments}\n"
            f"Ранг: {spec.rank}\n\n"
        )
    await message.answer(response, reply_markup=get_admin_keyboard())

@router.message(F.text == "📅 Записи")
async def show_appointments(message: Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id
    crud = CRUD(session)
    user = await crud.get_user(str(telegram_id))
    if not user or user.role != Role.ADMIN:
        await message.answer("У вас нет прав администратора!")
        return
    appointments = await crud.get_future_appointments()
    if not appointments:
        await message.answer("Нет запланированных заявок.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    APPOINTMENTS_PER_PAGE = 5
    page = 0
            if app.status != AppointmentStatus.CANCELED:
                buttons.append(
                    [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_appointment_{app.id}")]
                )
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"appointments_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"appointments_page_{page + 1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")])
        return response, InlineKeyboardMarkup(inline_keyboard=buttons)

    response, keyboard = get_appointments_page(page)
    await message.answer(response, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AdminStates.view_appointments)
    await state.update_data(total_pages=total_pages, appointments=appointments)

@router.callback_query(F.data.startswith("appointments_page_"), AdminStates.view_appointments)
async def paginate_appointments(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    appointments = data.get("appointments", [])
    total_pages = data.get("total_pages", 1)
    APPOINTMENTS_PER_PAGE = 5

    def get_appointments_page(page: int) -> tuple[str, InlineKeyboardMarkup]:
        start_idx = page * APPOINTMENTS_PER_PAGE
        end_idx = min(start_idx + APPOINTMENTS_PER_PAGE, len(appointments))
        response = f"<b>Запланированные заявки (Страница {page + 1}/{total_pages}):</b>\n\n"
        buttons = []
        for app in appointments[start_idx:end_idx]:
            status = app.status.value
            date = app.proposed_date.astimezone(config.TIMEZONE).strftime("%d.%m.%Y")
            scheduled_time = app.scheduled_time.astimezone(config.TIMEZONE).strftime(
                "%H:%M") if app.scheduled_time else "Не назначено"
            specialist = app.specialist.full_name if app.specialist else "Не назначен"
            reason = app.reason[:100] + "..." if len(app.reason) > 100 else app.reason
            response += (
                f"Заявка #{app.id}\n"
                f"Клиент: {app.client.full_name}\n"
                f"Дата: {date}\n"
                f"Время: {scheduled_time}\n"
                f"Специалист: {specialist}\n"
                f"Статус: {status}\n"
                f"Причина: {reason}\n\n"
            )
            if app.status != AppointmentStatus.CANCELED:
                buttons.append(
                    [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_appointment_{app.id}")]
                )
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"appointments_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"appointments_page_{page + 1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        butto
        await message.answer("Чёрный список пуст.", reply_markup=get_admin_keyboard())
        return
    response = "<b>Чёрный список:</b>\n\n"
    for entry in blacklist:
        response += (
            f"Пользователь: {entry.user_id}\n"
            f"Причина: {entry.reason}\n"
            f"Заблокирован до: {entry.blocked_until.astimezone(config.TIMEZONE).strftime('%d.%m.%Y %H:%M')}\n\n"
        )
    await message.answer(response, reply_markup=get_admin_keyboard())

@router.message(F.text == "🔨 работа с ЧС")
async def manage_blacklist(message: Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id
    crud = CRUD(session)
    user = await crud.get_user(str(telegram_id))
    if not user or user.role != Role.ADMIN:
        await message.answer("У вас нет прав администратора!")
        return
    blacklist = await crud.get_blacklist()
    if not blacklist:
        await message.answer("Чёрный список пуст.", reply_markup=get_admin_keyboard())
        return
    inline_buttons = [
        [InlineKeyboardButton(text="Добавить в ЧС", callback_data="add_to_blacklist")]
    ] + [
        [InlineKeyboardButton(text=f"Удалить из ЧС: {entry.user_id}",
                              callback_data=f"remove_from_blacklist_{entry.user_id}")]
        for entry in blacklist
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=inline_buttons)
    await message.answer("Выберите действие:", reply_markup=keyboard)
    await state.set_state(AdminStates.blacklist_management)

@router.callback_query(F.data == "add_to_blacklist", AdminStates.blacklist_management)
async def add_to_blacklist(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите Telegram ID пользователя для добавления в ЧС:")
    await state.set_state(AdminStates.adding_to_blacklist)

@router.message(AdminStates.adding_to_blacklist)
async def process_a
    await state.clear()

@router.callback_query(F.data.startswith("remove_from_blacklist_"), AdminStates.blacklist_management)
async def remove_from_blacklist(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    telegram_id = callback.data.split("_")[-1]
    crud = CRUD(session)
    blacklist_entry = await crud.is_blacklisted(telegram_id)
    if not blacklist_entry:
        await callback.message.edit_text("Пользователь не найден в ЧС.", reply_markup=None)
        await state.clear()
        return
    await session.de
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Добавить специалиста", callback_data="add_specialist")],
        [InlineKeyboardButton(text="Удалить специалиста", callback_data="remove_specialist")]
    ])
    await message.answer(response, reply_markup=keyboard)

@router.callback_query(F.data == "add_specialist")
async def add_specialist(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    crud = CRUD(session)
    clients = await crud.get_all_clients()
    if not clients:
        await callback.message.edit_text("Нет зарегистрированных клиентов.", reply_markup=None)
        await state.clear()
        return
    CLIENTS_PER_PAGE = 10
    page = 0
    total_pages = (len(clients) + CLIENTS_PER_PAGE - 1) // CLIENTS_PER_PAGE

    def get_client_keyboard(page: int) -> InlineKeyboardMarkup:
        start_idx = page * CLIENTS_PER_PAGE
        end_idx = min(start_idx + CLIENTS_PER_PAGE, len(clients))
        buttons = [
            [InlineKeyboardButton(
                text=f"{client.full_name} (ID: {client.user_id})",
                callback_data=f"select_client_{client.user_id}"
            )] for client in clients[start_idx:end_idx]
        ]
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page_{page + 1}"))
        if nav_buttons:session: AsyncSession):
    page = int(callback.data.split("_")[1])
    crud = CRUD(session)
    clients = await crud.get_all_clients()
    data = await state.get_data()
    total_pages = data.get("total_pages", 1)
    CLIENTS_PER_PAGE = 10

    def get_client_keyboard(page: int) -> InlineKeyboardMarkup:
        start_idx = page * CLIENTS_PER_PAGE
        end_idx = min(start_idx + CLIENTS_PER_PAGE, len(clients))
        buttons = [
            [InlineKeyboardButton(
                text=f"{client.full_name} (ID: {client.user_id})",
                callback_data=f"select_client_{client.user_id}"
            )] for client in clients[start_idx:end_idx]
        ]
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"page_{page + 1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton(text="Отмена", callback_data="cancel_add_specialist")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    keyboard = get_client_keyboard(page)
    await callback.message.edit_text(
        f"Выберите клиента для назначения специалистом (Страница {page + 1}/{total_pages}):",
        reply_markup=keyboard
    )

    if user.role != Role.CLIENT:
        await callback.message.edit_text(
            f"Пользователь {user.client.full_name} не может быть назначен специалистом (уже {user.role.value}).",
            reply_markup=None
        )
        await state.clear()
        return
    await state.update_data(telegram_id=telegram_id, full_name=user.client.full_name)
    await callback.message.edit_text(
        f"Назначаем специалиста: {user.client.full_name} (ID: {telegram_id})\n"
        f"Введите username (например: '@ivan') или оставьте как есть:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Оставить без username", callback_data=f"no_username_{telegram_id}")
            ]
        ])
    )
    await state.set_state(AdminStates.adding_specialist_details)

@router.message(AdminStates.adding_specialist_details)
async def process_add_specialist_details(message: Message, state: FSMContext, session: AsyncSession):
    username = message.text.strip() if message.text else ""
    if username and not username.startswith("@"):
        await message.answer("Username должен начинаться с '@' (например: '@ivan'). Повторите ввод:")
        return
    data = await state.get
    data = await state.get_data()
    full_name = data["full_name"]
    crud = CRUD(session)
    user = await crud.get_user(telegram_id)
    if not user:
        await callback.message.edit_text("Пользователь не найден.", reply_markup=None)
        await state.clear()
        return
    client = await crud.get_client(telegram_id)
    if not client:
        await callback.message.edit_text("Клиент не найден.", reply_markup=None)
        await state.clear()
        return
    user.role = Role.SPECIALIST
    await session.merge(user)
    specialist = Specialist(
        user_id=telegram_id,
        full_name=full_name,
        username=f"@{telegram_id}",
        phone=client.phone,
        is_available=True
    )
    try:
        await crud.create_specialist(specialist)
        await callback.message.edit_text(f"Специалист {full_name} добавлен.", reply_markup=None)
    except Exception as e:
        logger.error(f"Failed to create specialist {telegram_id}: {e}")
        await session.rollback()
        await callback.message.edit_text("Ошибка при добавлении специалиста. Попробуйте позже.", reply_markup=None)
    finally:
        await state.clear()

@router.callback_query(F.data == "remove_specialist")
async def remove_specialist(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите Telegram ID специалиста для удаления:")
    await state.set_state(AdminStates.removing_specialist)

@router.message(AdminStates.removing_specialist)
async def process_remove_specialist(message: Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.text.strip()
    crud = CRUD(session)
    specialist = await crud.get_specialist(telegram_id)
    if not specialist:
        await message.answer("Специалист не найден.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    user = await crud.get_user(telegram_id)
    if user:
        await session.delete(user)
    await session.delete(specialist)
    await session.commit()
    await message.answer(f"Специалист {telegram_id} удалён.", reply_markup=get_admin_keyboard())
    await state.clear()

@router.message(F.text == "📄 Экспорт данных")
async def export_data(message: Message, state: FSMContext, session: AsyncSession):
    telegram_id = message.from_user.id
    crud = CRUD(session)
    user = await crud.get_user(str(telegram_id))
    if not user or user.role != Role.ADMIN:
        await message.answer("У вас нет прав администратора!")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 неделя", callback_data="export_1week")],
        [InlineKeyboardButton(text="2 недели", callback_data="export_2weeks")],
        [InlineKeyboardButton(text="1 месяц", callback_data="export_1month")],
        [InlineKeyboardButton(text="Отмена", callback_data="cancel_export")]
    ])
    await message.answer("Выберите период для экспорта данных:", reply_markup=keyboard)
    await state.set_state(AdminStates.export_data)

@router.callback_query(F.data.startswith("export_"), AdminStates.export_data)
async def process_export(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    period = callback.data.split("_")[1]
    try:
        csv_content = await export_appointments_to_csv(session, period)
        filename = f"appointments_{period}_{datetime.now(tz=config.TIMEZONE).strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(csv_content)
        await callback.message.bot.send_document(
            chat_id=callback.message.chat.id,
            document=FSInputFile(filename),
            caption=f"Экспорт заявок за {period.replace('1week', '1 неделю').replace('2weeks', '2 недели').replace('1month', '1 месяц')}"
        )
        os.remove(filename)
    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        await callback.message.edit_text("Ошибка при экспорте данных. Попробуйте позже.", reply_markup=None)
    await state.clear()

@router.callback_query(F.data == "cancel_export", AdminStates.export_data)
async def cancel_export(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Экспорт данных отменён.", reply_markup=get_admin_keyboard())
    await state.clear()

@router.callback_query(F.data.startswith("confirm_"))
async def confirm_appointment(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    appointment_id = int(callback.data.split("_")[1])
    crud = CRUD(session)
    appointment = await crud.get_appointment(appointment_id)
    if not appointment:
        await callback.message.edit_text("Заявка не найдена.", reply_markup=None)
        await state.clear()
        return
    specialists = await crud.get_available_specialists()
    if not specialists:
        await callback.message.edit_text("Нет доступных специалистов.", reply_markup=None)
        await state.clear()
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{spec.full_name} (@{spec.username})",
                              callback_data=f"assign_{appointment_id}_{spec.user_id}")]
        for spec in specialists
    ])
    await callback.message.edit_text("Выберите специалиста:", reply_markup=keyboard)
    await state.set_state(AdminStates.select_specialist)

@router.callback_query(F.data.startswith("assign_"), AdminStates.select_specialist)
async def assign_specialist(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot):
    _, appointment_id, specialist_id = callback.data.split("_")
    appointment_id = int(appointment_id)
    crud = CRUD(session)
    appointment = await crud.get_appointment(appointment_id)
    if not appointment:
        await callback.message.edit_text("Заявка не найдена.", reply_markup=None)
        await state.clear()
        return
    specialist = await crud.get_specialist(specialist_id)
    if not specialist:
        await callback.message.edit_text("Специалист не найден.", reply_markup=None)
        await state.clear()
        return
    try:
        await bot.send_message(specialist.user_id, "Проверка доступности бота.")
    except TelegramBadRequest as e:
        logger.error(f"Cannot message specialist {specialist.user_id}: {e}")
        await callback.message.edit_text(
            f"Специалист {specialist.full_name} недоступен (возможно, бот заблокирован или ID неверный).",
            reply_markup=None
        )
        await state.clear()
        return
    appointment.specialist_id = specialist.id
    await session.commit()
    appointments = await crud.get_appointments_by_specialist(specialist.id)
    keyboard = get_time_selection_keyboard(appointments, appointment.proposed_date)
    await callback.message.edit_text("Выберите время:", reply_markup=keyboard)
    await state.update_data(appointment_id=appointment_id)
    await state.set_state(AdminStates.select_time)

@router.callback_query(F.data.startswith("time_"), AdminStates.select_time)
async def select_time(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot):
    time_str = callback.data.split("_")[1]
    data = await state.get_data()
    appointment_id = data["appointment_id"]
    crud = CRUD(session)
    appointment = await crud.get_appointment(appointment_id)
    if not appointment:
        await callback.message.edit_text("Заявка не найдена.", reply_markup=None)
        await state.clear()
        return
    scheduled_time = datetime.strptime(
        f"{appointment.proposed_date.strftime('%Y-%m-%d')} {time_str}",
        "%Y-%m-%d %H:%M"
    ).replace(tzinfo=config.TIMEZONE)
    appointment.scheduled_time = scheduled_time
    appointment.status = AppointmentStatus.APPROVED
    await session.commit()
    try:
        await notify_client_approved(bot, appointment)
    except Exception as e:
        logger.error(f"Failed to notify client for appointment {appointment_id}: {e}")
        await bot.send_message(
            config.ADMIN_ID,
            escape_markdown_v2(f"Ошибка: Не удалось уведомить клиента о подтверждении заявки #{appointment_id}."),
            parse_mode="MarkdownV2"
        )
    specialist = appointment.specialist
    scheduled_time_str = scheduled_time.astimezone(config.TIMEZONE).strftime("%d.%m.%Y %H:%M")
    client_link = f"https://t.me/{appointment.client.user_id}"
    client_contact = f"Контакт клиента: {client_link}"
    try:
        chat = await bot.get_chat(appointment.client.user_id)
        if chat.username:
            client_link = f"https://t.me/{chat.username}"
            client_contact = f"Контакт клиента: {client_link}"
        else:
            client_contact += f"\n(Если ссылка не работает, свяжитесь с администратором: https://t.me/{config.ADMIN_ID})"
    except TelegramBadRequest as e:
        logger.warning(
            f"Cannot get username for client {appointment.client.user_id} (appointment_id: {appointment_id}): {e}")
        client_contact += f"\n(Если ссылка не работает, свяжитесь с администратором: https://t.me/{config.ADMIN_ID})"
    try:
        text = (
            f"Новая заявка #{appointment.id} назначена на {scheduled_time_str}\n"
            f"Клиент: {appointment.client.full_name}\n"
            f"{client_contact}\n"
            f"Номер телефона клиента: {appointment.client.phone}\n"
            f"Причина: {appointment.reason[:500] + '...' if len(appointment.reason) > 500 else appointment.reason}"
        )
        escaped_text = escape_markdown_v2(text)
        await bot.send_message(
            specialist.user_id,
            escaped_text,
            parse_mode="MarkdownV2"
        )
    except TelegramBadRequest as e:
        logger.error(f"Failed to notify specialist {specialist.user_id} for appointment {appointment_id}: {e}")
        await bot.send_message(
            config.ADMIN_ID,
            f"Ошибка: Не удалось уведомить специалиста {specialist.full_name} (ID: {specialist.user_id}) о заявке #{appointment.id}. Причина: {e}"
        )
        specialist.is_available = False
        await session.commit()
    await callback.message.edit_text(f"Заявка #{appointment.id} подтверждена на {scheduled_time_str}.",
                                    reply_markup=None)
    await state.clear()

@router.callback_query(F.data.startswith("cancel_appointment_"))
async def cancel_appointment(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot):
    appointment_id = int(callback.data.split("_")[2])
    crud = CRUD(session)
    appointment = await crud.get_appointment(appointment_id)
    if not appointment:
        await callback.message.edit_text("Заявка не найдена.", reply_markup=None)
        await state.clear()
        return
    await callback.message.edit_text(
        "Введите причину отклонения заявки:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отменить действие", callback_data="abort_reject")]
        ])
    )
    await state.update_data(appointment_id=appointment_id)
    await state.set_state(AdminStates.reject_reason)

@router.message(AdminStates.reject_reason)
async def process_reject_reason(message: Message, state: FSMContext, session: AsyncSession, bot):
    reason = message.text.strip()
    if not reason:
        await message.answer("Причина не может быть пустой. Введите снова:")
        return
    data = await state.get_data()
    appointment_id = data.get("appointment_id")
    if not appointment_id:
        await message.answer("Ошибка: заявка не найдена.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    crud = CRUD(session)
    try:
        appointment = await crud.get_appointment(appointment_id)
        if not appointment:
            await message.answer("Заявка не найдена.", reply_markup=get_admin_keyboard())
            await state.clear()
            return
        if not appointment.client or not appointment.client.user:
            logger.error(f"Invalid appointment {appointment_id}: missing client or user relationship")
            await message.answer("Ошибка: данные клиента недоступны.", reply_markup=get_admin_keyboard())
            await state.clear()
            return
        logger.debug(f"Updating appointment {appointment_id}: status=CANCELED, reason={reason}")
        appointment.status = AppointmentStatus.CANCELED
        appointment.reject_reason = reason
        await session.commit()
        from services.notifications import notify_client_rejected
        try:
            await notify_client_rejected(bot, appointment, reason)
        except Exception as e:
            logger.warning(f"Failed to notify client {appointment.client.user.telegram_id} for appointment {appointment_id}: {e}")
            await bot.send_message(
                config.ADMIN_ID,
                escape_markdown_v2(f"Ошибка: Не удалось уведомить клиента о заявке #{appointment.id}."),
                parse_mode="MarkdownV2"
            )
        await message.answer(f"Заявка #{appointment.id} отклонена.", reply_markup=get_admin_keyboard())
        logger.info(f"Admin {message.from_user.id} rejected appointment {appointment_id}: {reason}")
    except Exception as e:
        logger.error(f"Failed to reject appointment {appointment_id} by admin {message.from_user.id}: {e}", exc_info=True)
        await session.rollback()
        await message.answer("Ошибка при отклонении заявки. Попробуйте позже.", reply_markup=get_admin_keyboard())
    finally:
        await state.clear()

@router.callback_query(F.data.startswith("cancel_"))
async def reject_new_appointment(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot):
    telegram_id = callback.from_user.id
    crud = CRUD(session)
    user = await crud.get_user(str(telegram_id))
    if not user or user.role != Role.ADMIN:
        await callback.message.edit_text("У вас нет прав администратора.", reply_markup=None)
        await callback.answer()
        return
    try:
        appointment_id = int(callback.data.split("_")[1])
        appointment = await crud.get_appointment(appointment_id)
        if not appointment:
            await callback.message.edit_text("Заявка не найдена.", reply_markup=None)
            await callback.answer()
            return
        await callback.message.edit_text(
            "Введите причину отклонения заявки:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Отменить действие", callback_data="abort_reject")]
            ])
        )
        await state.update_data(appointment_id=appointment_id)
        await state.set_state(AdminStates.reject_reason)
        logger.info(f"Admin {telegram_id} initiated rejection for new appointment {appointment_id}")
        await callback.answer()
    except ValueError as e:
        logger.error(f"Invalid appointment_id in callback data: {callback.data}, error: {e}")
        await callback.message.edit_text("Ошибка: неверный ID заявки.", reply_markup=None)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error rejecting new appointment for admin {telegram_id}: {e}", exc_info=True)
        await session.rollback()
        await callback.message.edit_text("Ошибка при обработке заявки. Попробуйте позже.", reply_markup=None)
        await callback.answer()

@router.callback_query(F.data == "abort_reject", AdminStates.reject_reason)
async def abort_reject(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Действие отклонения заявки отменено.", reply_markup=None)
    await state.clear()

@router.message(F.text == "📋 Назначенные встречи")
async def show_assigned_appointments(message: Message, state: FSMContext, session: AsyncSession):
    """Show list of specialists to view their assigned appointments."""
    telegram_id = message.from_user.id
    crud = CRUD(session)
    user = await crud.get_user(str(telegram_id))
    if not user or user.role != Role.ADMIN:
        await message.answer("У вас нет прав администратора!")
        return
    specialists = await crud.get_all_specialists()
    if not specialists:
        await message.answer("Нет зарегистрированных специалистов.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    SPECIALISTS_PER_PAGE = 10
    page = 0
    total_pages = (len(specialists) + SPECIALISTS_PER_PAGE - 1) // SPECIALISTS_PER_PAGE

    def get_specialists_page(page: int) -> tuple[str, InlineKeyboardMarkup]:
        start_idx = page * SPECIALISTS_PER_PAGE
        end_idx = min(start_idx + SPECIALISTS_PER_PAGE, len(specialists))
        response = f"<b>Список специалистов (Страница {page + 1}/{total_pages}):</b>\n\n"
        buttons = []
        for spec in specialists[start_idx:end_idx]:
            username = f"@{spec.username}" if spec.username else f"ID: {spec.user_id}"
            response += f"Специалист: {spec.full_name} ({username})\n"
            buttons.append(
                [InlineKeyboardButton(text=f"{spec.full_name}", callback_data=f"view_specialist_{spec.user_id}")]
            )
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"specialists_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"specialists_page_{page + 1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")])
        return response, InlineKeyboardMarkup(inline_keyboard=buttons)

    response, keyboard = get_specialists_page(page)
    await message.answer(response, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AdminStates.view_specialists)
    await state.update_data(total_pages=total_pages, specialists=specialists)

@router.callback_query(F.data.startswith("specialists_page_"), AdminStates.view_specialists)
async def paginate_specialists(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Paginate through specialists list."""
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    specialists = data.get("specialists", [])
    total_pages = data.get("total_pages", 1)
    SPECIALISTS_PER_PAGE = 10

    def get_specialists_page(page: int) -> tuple[str, InlineKeyboardMarkup]:
        start_idx = page * SPECIALISTS_PER_PAGE
        end_idx = min(start_idx + SPECIALISTS_PER_PAGE, len(specialists))
        response = f"<b>Список специалистов (Страница {page + 1}/{total_pages}):</b>\n\n"
        buttons = []
        for spec in specialists[start_idx:end_idx]:
            username = f"@{spec.username}" if spec.username else f"ID: {spec.user_id}"
            response += f"Специалист: {spec.full_name} ({username})\n"
            buttons.append(
                [InlineKeyboardButton(text=f"{spec.full_name}", callback_data=f"view_specialist_{spec.user_id}")]
            )
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"specialists_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"specialists_page_{page + 1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")])
        return response, InlineKeyboardMarkup(inline_keyboard=buttons)

    response, keyboard = get_specialists_page(page)
    await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("view_specialist_"), AdminStates.view_specialists)
async def view_specialist_appointments(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Show assigned appointments for a selected specialist."""
    specialist_id = callback.data.split("_")[-1]
    crud = CRUD(session)
    specialist = await crud.get_specialist(specialist_id)
    if not specialist:
        await callback.message.edit_text("Специалист не найден.", reply_markup=None)
        await state.clear()
        return
    appointments = await crud.get_appointments_by_specialist(specialist_id)
    appointments = [app for app in appointments if app.status in [AppointmentStatus.APPROVED, AppointmentStatus.PENDING]]
    if not appointments:
        await callback.message.edit_text(
            f"Нет назначенных заявок для специалиста {specialist.full_name}.",
            reply_markup=get_admin_inline_keyboard()
        )
        await state.clear()
        return
    APPOINTMENTS_PER_PAGE = 5
    page = 0
    total_pages = (len(appointments) + APPOINTMENTS_PER_PAGE - 1) // APPOINTMENTS_PER_PAGE

    def get_appointments_page(page: int) -> tuple[str, InlineKeyboardMarkup]:
        start_idx = page * APPOINTMENTS_PER_PAGE
        end_idx = min(start_idx + APPOINTMENTS_PER_PAGE, len(appointments))
        response = f"<b>Заявки специалиста {specialist.full_name} (Страница {page + 1}/{total_pages}):</b>\n\n"
        buttons = []
        for app in appointments[start_idx:end_idx]:
            scheduled_time = app.scheduled_time.astimezone(config.TIMEZONE).strftime(
                "%d.%m.%Y %H:%M") if app.scheduled_time else "Не назначено"
            reason = app.reason[:100] + "..." if len(app.reason) > 100 else app.reason
            response += (
                f"Заявка #{app.id}\n"
                f"Клиент: {app.client.full_name}\n"
                f"Время: {scheduled_time}\n"
                f"Статус: {app.status.value}\n"
                f"Причина: {reason}\n\n"
            )
            if app.status == AppointmentStatus.APPROVED:
                buttons.append(
                    [InlineKeyboardButton(text="🔄 Переназначить", callback_data=f"reassign_{app.id}")]
                )
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"spec_appointments_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"spec_appointments_page_{page + 1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton(text="Назад к специалистам", callback_data="back_to_specialists")])
        return response, InlineKeyboardMarkup(inline_keyboard=buttons)

    response, keyboard = get_appointments_page(page)
    await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AdminStates.view_specialist_appointments)
    await state.update_data(specialist_id=specialist_id, total_pages=total_pages, appointments=appointments)

@router.callback_query(F.data.startswith("spec_appointments_page_"), AdminStates.view_specialist_appointments)
async def paginate_specialist_appointments(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Paginate through specialist's appointments."""
    page = int(callback.data.split("_")[-1])
    data = await state.get_data()
    specialist_id = data.get("specialist_id")
    appointments = data.get("appointments", [])
    total_pages = data.get("total_pages", 1)
    APPOINTMENTS_PER_PAGE = 5
    crud = CRUD(session)
    specialist = await crud.get_specialist(specialist_id)
    if not specialist:
        await callback.message.edit_text("Специалист не найден.", reply_markup=None)
        await state.clear()
        return

    def get_appointments_page(page: int) -> tuple[str, InlineKeyboardMarkup]:
        start_idx = page * APPOINTMENTS_PER_PAGE
        end_idx = min(start_idx + APPOINTMENTS_PER_PAGE, len(appointments))
        response = f"<b>Заявки специалиста {specialist.full_name} (Страница {page + 1}/{total_pages}):</b>\n\n"
        buttons = []
        for app in appointments[start_idx:end_idx]:
            scheduled_time = app.scheduled_time.astimezone(config.TIMEZONE).strftime(
                "%d.%m.%Y %H:%M") if app.scheduled_time else "Не назначено"
            reason = app.reason[:100] + "..." if len(app.reason) > 100 else app.reason
            response += (
                f"Заявка #{app.id}\n"
                f"Клиент: {app.client.full_name}\n"
                f"Время: {scheduled_time}\n"
                f"Статус: {app.status.value}\n"
                f"Причина: {reason}\n\n"
            )
            if app.status == AppointmentStatus.APPROVED:
                buttons.append(
                    [InlineKeyboardButton(text="🔄 Переназначить", callback_data=f"reassign_{app.id}")]
                )
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"spec_appointments_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"spec_appointments_page_{page + 1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton(text="Назад к специалистам", callback_data="back_to_specialists")])
        return response, InlineKeyboardMarkup(inline_keyboard=buttons)

    response, keyboard = get_appointments_page(page)
    await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "back_to_specialists", AdminStates.view_specialist_appointments)
async def back_to_specialists(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Return to specialists list."""
    crud = CRUD(session)
    specialists = await crud.get_all_specialists()
    if not specialists:
        await callback.message.edit_text("Нет зарегистрированных специалистов.", reply_markup=get_admin_keyboard())
        await state.clear()
        return
    SPECIALISTS_PER_PAGE = 10
    page = 0
    total_pages = (len(specialists) + SPECIALISTS_PER_PAGE - 1) // SPECIALISTS_PER_PAGE

    def get_specialists_page(page: int) -> tuple[str, InlineKeyboardMarkup]:
        start_idx = page * SPECIALISTS_PER_PAGE
        end_idx = min(start_idx + SPECIALISTS_PER_PAGE, len(specialists))
        response = f"<b>Список специалистов (Страница {page + 1}/{total_pages}):</b>\n\n"
        buttons = []
        for spec in specialists[start_idx:end_idx]:
            username = f"@{spec.username}" if spec.username else f"ID: {spec.user_id}"
            response += f"Специалист: {spec.full_name} ({username})\n"
            buttons.append(
                [InlineKeyboardButton(text=f"{spec.full_name}", callback_data=f"view_specialist_{spec.user_id}")]
            )
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"specialists_page_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ➡️", callback_data=f"specialists_page_{page + 1}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton(text="Назад в меню", callback_data="back_to_menu")])
        return response, InlineKeyboardMarkup(inline_keyboard=buttons)

    response, keyboard = get_specialists_page(page)
    await callback.message.edit_text(response, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(AdminStates.view_specialists)
    await state.update_data(total_pages=total_pages, specialists=specialists)
    await callback.answer()

@router.callback_query(F.data.startswith("reassign_"), AdminStates.view_specialist_appointments)
async def reassign_appointment(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Initiate reassignment of an appointment to another specialist."""
    appointment_id = int(callback.data.split("_")[1])
    crud = CRUD(session)
    appointment = await crud.get_appointment(appointment_id)
    if not appointment:
        await callback.message.edit_text("Заявка не найдена.", reply_markup=None)
        await state.clear()
        return
    if not appointment.scheduled_time:
        await callback.message.edit_text("Заявка не имеет назначенного времени.", reply_markup=None)
        await state.clear()
        return
    specialists = await crud.get_available_specialists()
    specialists = [spec for spec in specialists if spec.id != appointment.specialist_id]
    if not specialists:
        await callback.message.edit_text("Нет доступных специалистов для переназначения.", reply_markup=None)
        await state.clear()
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{spec.full_name} (@{spec.username})",
                              callback_data=f"reassign_to_{appointment_id}_{spec.user_id}")]
        for spec in specialists
    ])
    await callback.message.edit_text("Выберите нового специалиста:", reply_markup=keyboard)
    await state.set_state(AdminStates.reassign_specialist)
    await state.update_data(appointment_id=appointment_id)

@router.callback_query(F.data.startswith("reassign_to_"), AdminStates.reassign_specialist)
async def process_reassign_specialist(callback: CallbackQuery, state: FSMContext, session: AsyncSession, bot):
    """Process reassignment to a new specialist and send notifications."""
    _, appointment_id, new_specialist_id = callback.data.split("_")
    appointment_id = int(appointment_id)
    crud = CRUD(session)
    appointment = await crud.get_appointment(appointment_id)
    if not appointment:
        await callback.message.edit_text("Заявка не найдена.", reply_markup=None)
        await state.clear()
        return
    old_specialist = appointment.specialist
    new_specialist = await crud.get_specialist(new_specialist_id)
    if not new_specialist:
        await callback.message.edit_text("Специалист не найден.", reply_markup=None)
        await state.clear()
        return
    try:
        await bot.send_message(new_specialist.user_id, "Проверка доступности бота.")
    except TelegramBadRequest as e:
        logger.error(f"Cannot message specialist {new_specialist.user_id}: {e}")
        await callback.message.edit_text(
            f"Специалист {new_specialist.full_name} недоступен (возможно, бот заблокирован или ID неверный).",
            reply_markup=None
        )
        await state.clear()
        return
    appointment.specialist_id = new_specialist.id
    appointment.client_ready = False
    appointment.specialist_ready = False
    await session.commit()
    try:
        await notify_client_reassigned(bot, appointment)
    except Exception as e:
        logger.error(f"Failed to notify client for reassigned appointment {appointment_id}: {e}")
        await bot.send_message(
            config.ADMIN_ID,
            escape_markdown_v2(f"Ошибка: Не удалось уведомить клиента о переназначении заявки #{appointment_id}."),
            parse_mode="MarkdownV2"
        )
    try:
        await notify_specialist(bot, appointment, is_reassignment=True)
    except Exception as e:
        logger.error(f"Failed to notify new specialist {new_specialist.user_id} for reassigned appointment {appointment_id}: {e}")
        await bot.send_message(
            config.ADMIN_ID,
            escape_markdown_v2(f"Ошибка: Не удалось уведомить специалиста {new_specialist.full_name} о переназначении заявки #{appointment_id}."),
            parse_mode="MarkdownV2"
        )
        new_specialist.is_available = False
        await session.commit()
    if old_specialist and old_specialist.is_available:
        try:
            text = escape_markdown_v2(
                f"Заявка #{appointment.id} была переназначена на другого специалиста.\n"
                f"Клиент: {appointment.client.full_name}\n"
                f"Время: {appointment.scheduled_time.astimezone(config.TIMEZONE).strftime('%d.%m.%Y %H:%M')}"
            )
            await bot.send_message(
                old_specialist.user_id,
                text,
                parse_mode="MarkdownV2"
            )
        except TelegramBadRequest as e:
            logger.warning(f"Failed to notify old specialist {old_specialist.user_id} for reassigned appointment {appointment_id}: {e}")
    await callback.message.edit_text(
        f"Заявка #{appointment.id} переназначена на {new_specialist.full_name}.",
        reply_markup=None
    )
    await state.clear()
