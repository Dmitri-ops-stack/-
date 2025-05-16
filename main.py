import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramAPIError, TelegramNetworkError, TelegramServerError
from config import config, storage
from database.models import Base, Appointment, AppointmentStatus, Client, Specialist, NotificationSent
from database.database import engine, get_session, create_session, dispose_engine
from handlers import client, admin, specialist
from database.crud import CRUD
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import joinedload

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Обработчик ошибок обновлений
async def on_error(update, exception):
    logger.debug("Error handler triggered")
    logger.error(f"Update {update.update_id} failed: {exception}", exc_info=True)
    try:
        await Bot.get_current().send_message(
            config.ADMIN_ID,
            f"Bot error: {exception}",
            parse_mode=ParseMode.HTML
        )
    except Exception as e:
        logger.error(f"Failed to notify admin of error: {e}")
    return True  # Продолжить обработку других обновлений

# Миддлварь для предоставления session и bot
async def on_startup(dispatcher: Dispatcher, bot: Bot):
    logger.info("Setting up session middleware")
    async def session_middleware(handler, event, data):
        async with create_session() as session:
            data["session"] = session
            data["bot"] = bot
            return await handler(event, data)
    dispatcher.update.outer_middleware.register(session_middleware)
    dispatcher.error.register(on_error)  # Регистрация обработчика ошибок

# Фоновая задача для отправки напоминаний
async def send_reminders(bot: Bot):
    logger.debug("Starting reminder task")
    last_run = datetime.now(tz=config.TIMEZONE)
    while True:
        try:
            now = datetime.now(tz=config.TIMEZONE)
            if (now - last_run).total_seconds() < 60:
                await asyncio.sleep(60 - (now - last_run).total_seconds())
                continue
            last_run = now
            async with create_session() as session:
                crud = CRUD(session)
                logger.debug(
                    f"Checking reminders for window: {now - timedelta(minutes=1)} to {now + timedelta(hours=1, minutes=1)}")
                appointments = await session.execute(
                    select(Appointment)
                    .where(
                        and_(
                            Appointment.status == AppointmentStatus.APPROVED,
                            Appointment.scheduled_time >= now - timedelta(minutes=1),
                            Appointment.scheduled_time <= now + timedelta(hours=1, minutes=1)
                        )
                    )
                    .options(
                        joinedload(Appointment.client).joinedload(Client.user),
                        joinedload(Appointment.specialist)
                    )
                )
                appointments = appointments.scalars().all()
                logger.debug(f"Found {len(appointments)} appointments for reminders")
                if not appointments:
                    logger.info("No appointments found for reminders")
                    await session.commit()
                    continue
                for app in appointments:
                    client = app.client
                    specialist = app.specialist
                    if not (client and specialist and client.user and specialist.user_id):
                        logger.warning(f"Invalid client or specialist for appointment {app.id}")
                        continue
                    scheduled_time = app.scheduled_time.astimezone(config.TIMEZONE)
                    time_until = (scheduled_time - now).total_seconds() / 60
                    logger.debug(f"Appointment {app.id}: time until {time_until:.2f} minutes")
                    sent_notifications = await crud.get_sent_notifications(app.id)
                    sent_types = {n.reminder_type for n in sent_notifications}
                    reminder_type = None
                    if 59 <= time_until <= 61 and '1h' not in sent_types:
                        reminder_type = '1h'
                    elif 4 <= time_until <= 6 and '5m' not in sent_types:
                        reminder_type = '5m'
                    if reminder_type:
                        formatted_time = scheduled_time.strftime("%H:%M")
                        try:
                            await bot.send_message(
                                client.user.telegram_id,
                                f"⏰ Напоминание: ваша заявка #{app.id} в {formatted_time} "
                                f"с <a href='tg://user?id={specialist.user_id}'>{specialist.full_name}</a>!",
                                parse_mode=ParseMode.HTML
                            )
                            await bot.send_message(
                                specialist.user_id,
                                f"⏰ Напоминание: заявка #{app.id} с "
                                f"<a href='tg://user?id={client.user.telegram_id}'>{client.full_name}</a> в {formatted_time}!",
                                parse_mode=ParseMode.HTML
                            )
                            await crud.create_notification_sent(app.id, reminder_type)
                            await session.commit()
                            logger.info(
                                f"Sent {reminder_type} reminder for appointment {app.id} to client {client.user.telegram_id} and specialist {specialist.user_id}")
                        except TelegramAPIError as e:
                            logger.error(f"Failed to send {reminder_type} reminder for appointment {app.id}: {e}",
                                         exc_info=True)
                            continue
                        except Exception as e:
                            logger.error(f"Unexpected error processing reminder for appointment {app.id}: {e}",
                                         exc_info=True)
                            continue
        except Exception as e:
            logger.error(f"Reminder task failed: {e}", exc_info=True)
        await asyncio.sleep(60)

# Фоновая задача для проверки опозданий клиентов и активности специалистов
async def check_late_clients(bot: Bot):
    logger.debug("Starting late client check task")
    last_run = datetime.now(tz=config.TIMEZONE)
    while True:
        try:
            now = datetime.now(tz=config.TIMEZONE)
            if (now - last_run).total_seconds() < 30:  # Run every 30 seconds for precision
                await asyncio.sleep(30 - (now - last_run).total_seconds())
                continue
            last_run = now
            async with create_session() as session:
                crud = CRUD(session)
                logger.debug(
                    f"Checking late clients for window: {now - timedelta(minutes=20)} to {now + timedelta(minutes=1)}")
                appointments = await session.execute(
                    select(Appointment)
                    .where(
                        and_(
                            Appointment.status == AppointmentStatus.APPROVED,
                            Appointment.scheduled_time <= now + timedelta(minutes=1),
                            Appointment.scheduled_time >= now - timedelta(minutes=20)
                        )
                    )
                    .options(
                        joinedload(Appointment.client).joinedload(Client.user),
                        joinedload(Appointment.specialist)
                    )
                )
                appointments = appointments.scalars().all()
                logger.debug(f"Found {len(appointments)} appointments for late client check")
                if not appointments:
                    logger.info("No appointments found for late client check")
                    await session.commit()
                    continue
                for app in appointments:
                    if app.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELED]:
                        logger.debug(f"Skipping appointment {app.id} with status {app.status}")
                        continue
                    client = app.client
                    specialist = app.specialist
                    if not (client and specialist and client.user and specialist.user_id):
                        logger.warning(f"Invalid client or specialist for appointment {app.id}")
                        continue
                    scheduled_time = app.scheduled_time.astimezone(config.TIMEZONE)
                    time_since = (now - scheduled_time).total_seconds() / 60
                    logger.debug(f"Appointment {app.id}: time since {time_since:.2f} minutes")
                    sent_notifications = await crud.get_sent_notifications(app.id)
                    sent_types = {n.reminder_type for n in sent_notifications}
                    try:
                        if time_since >= 20:
                            await crud.add_to_blacklist(
                                telegram_id=client.user.telegram_id,
                                reason="Опоздание на назначенное время (20 минут ожидания)",
                                duration_days=14
                            )
                            await bot.send_message(
                                client.user.telegram_id,
                                "🚫 Вы добавлены в чёрный список на 2 недели за опоздание. "
                                f"Специалист <a href='tg://user?id={specialist.user_id}'>{specialist.full_name}</a> "
                                "ждал вас 20 минут.",
                                parse_mode=ParseMode.HTML
                            )
                            app.status = AppointmentStatus.CANCELED
                            await session.commit()
                            logger.info(f"Client {client.user.telegram_id} blacklisted for appointment {app.id}")
                        elif time_since >= 10 and 'admin_no_ready' not in sent_types:
                            if specialist.is_available or 'specialist_ready' in sent_types:
                                logger.debug(f"Skipping admin_no_ready for appointment {app.id}: specialist is ready")
                                continue
                            await bot.send_message(
                                config.ADMIN_ID,
                                f"🚨 Специалист <a href='tg://user?id={specialist.user_id}'>{specialist.full_name}</a> "
                                f"не вышел на связь по заявке #{app.id} с "
                                f"<a href='tg://user?id={client.user.telegram_id}'>{client.full_name}</a> "
                                f"(время: {scheduled_time.strftime('%d.%m.%Y %H:%M')}).",
                                parse_mode=ParseMode.HTML
                            )
                            await crud.create_notification_sent(app.id, 'admin_no_ready')
                            await session.commit()
                            logger.info(
                                f"Sent admin notification for specialist {specialist.user_id} for appointment {app.id}")
                        elif -0.5 <= time_since <= 0.5 and 'ready' not in sent_types:  # ±30 seconds
                            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="✅ Готов к работе", callback_data=f"client_ready_{app.id}")],
                                [InlineKeyboardButton(text="❌ Отказаться", callback_data=f"client_refuse_{app.id}")]
                            ])
                            specialist_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="✅ Готов к работе", callback_data=f"specialist_ready_{app.id}")]
                            ])
                            await bot.send_message(
                                client.user.telegram_id,
                                f"🕒 Ваша заявка #{app.id} начинается сейчас! Вы готовы? "
                                f"Специалист: <a href='tg://user?id={specialist.user_id}'>{specialist.full_name}</a>",
                                parse_mode=ParseMode.HTML,
                                reply_markup=keyboard
                            )
                            await bot.send_message(
                                specialist.user_id,
                                f"🕒 Заявка #{app.id} с клиентом {client.full_name} начинается сейчас! Вы готовы?",
                                parse_mode=ParseMode.HTML,
                                reply_markup=specialist_keyboard
                            )
                            await crud.create_notification_sent(app.id, 'ready')
                            await session.commit()
                            logger.info(
                                f"Sent readiness prompt for appointment {app.id} to client {client.user.telegram_id} and specialist {specialist.user_id}")
                    except TelegramAPIError as e:
                        logger.error(f"Failed to process appointment {app.id}: {e}", exc_info=True)
                        continue
                    except Exception as e:
                        logger.error(f"Unexpected error processing late client check for appointment {app.id}: {e}",
                                     exc_info=True)
                        continue
        except Exception as e:
            logger.error(f"Late client check task failed: {e}", exc_info=True)
        await asyncio.sleep(30)  # Run every 30 seconds

# Фоновая задача для сброса рангов специалистов
async def reset_specialist_ranks(bot: Bot):
    logger.debug("Starting specialist rank reset task")
    last_run = datetime.now(tz=config.TIMEZONE)
    while True:
        try:
            now = datetime.now(tz=config.TIMEZONE)
            if (now - last_run).total_seconds() < 60:
                await asyncio.sleep(60 - (now - last_run).total_seconds())
                continue
            last_run = now
            if now.month == 1 and now.day == 1 and now.hour == 0 and now.minute == 0:
                async with create_session() as session:
                    crud = CRUD(session)
                    specialists = await crud.get_all_specialists()
                    logger.debug(f"Found {len(specialists)} specialists for rank reset")
                    for spec in specialists:
                        spec.completed_appointments = 0
                        spec.rank = 0
                        try:
                            await bot.send_message(
                                spec.user_id,
                                "📢 Ранги специалистов сброшены! Начните новый год с чистого листа!",
                                parse_mode=ParseMode.HTML
                            )
                            logger.info(f"Reset rank for specialist {spec.user_id}")
                        except TelegramAPIError as e:
                            logger.error(f"Failed to send rank reset message to specialist {spec.user_id}: {e}",
                                         exc_info=True)
                    await session.commit()
        except Exception as e:
            logger.error(f"Specialist rank reset task failed: {e}", exc_info=True)
        await asyncio.sleep(60)

async def main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
    async with create_session() as session:
        crud = CRUD(session)
        removed = await crud.remove_invalid_specialists()
        logger.info(f"Removed {removed} invalid specialists")
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)
    await on_startup(dp, bot)
    dp.include_router(client.router)
    dp.include_router(admin.router)
    dp.include_router(specialist.router)
    tasks = [
        asyncio.create_task(send_reminders(bot)),
        asyncio.create_task(check_late_clients(bot)),
        asyncio.create_task(reset_specialist_ranks(bot))
    ]
    logger.info("Background tasks started")
    async with create_session() as session:
        crud = CRUD(session)
        now = datetime.now(tz=config.TIMEZONE)
        expired_appointments = await session.execute(
            select(Appointment)
            .where(
                or_(
                    Appointment.status != AppointmentStatus.APPROVED,
                    Appointment.scheduled_time < now - timedelta(minutes=20)
                )
            )
        )
        expired_appointments = expired_appointments.scalars().all()
        if expired_appointments:
            for app in expired_appointments:
                await session.execute(
                    delete(NotificationSent)
                    .where(NotificationSent.appointment_id == app.id)
                )
            await session.commit()
            logger.info(f"Cleaned up {len(expired_appointments)} expired notification records")
        else:
            logger.debug("No expired notification records to clean up")
        all_appointments = await session.execute(
            select(Appointment)
        )
        all_appointments = all_appointments.scalars().all()
        approved_appointments = [app for app in all_appointments if app.status == AppointmentStatus.APPROVED]
        logger.info(
            f"Found {len(all_appointments)} total appointments, {len(approved_appointments)} with status APPROVED")
    retry_count = 0
    max_retries = 5
    while retry_count < max_retries:
        try:
            logger.info(f"Starting polling (attempt {retry_count + 1}/{max_retries})")
            await dp.start_polling(bot, handle_signals=True)
            break
        except (TelegramNetworkError, TelegramServerError) as e:
            retry_count += 1
            logger.error(f"Polling failed due to {e}. Retrying {retry_count}/{max_retries} after 10 seconds")
            await asyncio.sleep(10)
        except KeyboardInterrupt:
            logger.info("Received KeyboardInterrupt, stopping bot")
            break
        except Exception as e:
            logger.error(f"Unexpected error during polling: {e}", exc_info=True)
            retry_count += 1
            await asyncio.sleep(10)
    else:
        logger.error(f"Max retries ({max_retries}) reached. Stopping bot")
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await bot.session.close()
    await dispose_engine()
    logger.info("Database engine disposed")

if __name__ == "__main__":
    asyncio.run(main())