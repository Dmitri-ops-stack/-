import asyncio
import logging
from aiog
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
         
                                [InlineKeyboardButton(text="❌ Отказаться", callback_data=f"client_refuse_{app.id}")]
                            ])
                            specialist_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="✅ Готов к работе", callback_data=f"specialist_ready_{app.id}")]
                         
    logger.info("Database engine disposed")

if __name__ == "__main__":
    asyncio.run(main())
