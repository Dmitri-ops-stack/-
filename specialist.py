from aiogram import Router, F
from aiogram.filters import Command
f
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
    user = awa

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
    appoint
        await message.answer(response, parse_mode="MarkdownV2", reply_markup=markup)
        await state.set_state(SpecialistStates.rating_client)
        await state.update_data(client_id=client_id, appointment_id=appointment_id)
        lating}")
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
    if not
    data = await state.get_data()
    appointment_id 
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
    total_page
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
        logger.info(f"S
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
            client_messagодтверждена.",
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
    if page + 1 >= total_pages:ine_keyboard)
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
    if not specialist:ist.)
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
            f"До следующего ранга ({next_rank}): {progress} заявок"
        )
        has_appointments, _ = await has_active_appointment(session, specialist.id)
        keyboard = get_specialist_keyboard(has_appointments=has_appointments)
        await message.answer(response, parse_mode="MarkdownV2", reply_markup=keyboard)
        logger.info(f"Specialist {telegram_id} viewed rank")
    except Exception as e:
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
        response = escape_markdown_v2
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

    """Handle inv
    appointments = await crud.get_appointments_by_specialist(specialist.id)
    if not appointments:
        await message.
        logger.info(f"Specialist {telegram_id} submitted report: {report_text[:50]}...")
    except Exception as e:
        logger.error(f"Failed to save or notify admin for report by specialist {telegram_id}: {e}", exc_info=True)
        await session.rollback()
        await message.answer("Ошибка при отправке отчета. Попробуйте позже.")
    await state.clear()
