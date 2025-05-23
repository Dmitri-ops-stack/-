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
            if (no
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
               
                async with create_session() as session:
                    crud = CRUD(session)
             
    await asyncio.gather(*tasks, return_exceptions=True)
    await bot.session.close()
    await dispose_engine()
    logger.info("Database engine disposed")

if __name__ == "__main__":
    asyncio.run(main())
