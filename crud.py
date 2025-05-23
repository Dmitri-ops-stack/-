from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
fr
        logger.debug(f"Fetched user with telegram_id={telegram_id}")
        return user

    async def create_client(self, client: Client):
        """
        Создает нового клиента.
        """
        self.session.add(client)
        await self.session.commit()
        logger.info(f"Created client with user_id={client.user_id}, full_name={client.full_name}")
        return client

    async def get_client(self, telegram_id: str):
        """
        Получает клиента по telegram_id пользователя.
        """
        user = await self.get_user(telegram_id)
        if user and user.client:
            logger.debug(f"Fetched client for telegram_id={telegram_id}")
            return user.client
        logger.debug(f"No client found for telegram_id={telegram_id}")
        return None

    async def get_all_clients(self):
        """
        Получает всех клиентов.
        

    async def get_specialist(self, telegram_id: str):
        """
        Получает специалиста по telegram_id пользователя.
        """
        result = await self.session.execute(
            select(Specialist)
            .where(Specialist.user_id == telegram_id)
            .options(joinedload(Specialist.user))
        )
        specialist = result.scalars().first()
        logger.debug(f"Fetched specialist for telegram_id={telegram_id}")
        return specialist

    async def get_available_specialists(self):
        """
        Получает список доступных специалистов.
        

    async def create_appointment(self, appointment: Appointment):
        """
        Создает новую заявку.
        """
        self.session.add(appointment)
        await self.session.commit()
        logger.info(f"Created appointment id={appointment.id}, client_id={appointment.client_id}")
        return appointment

    async def get_appointment(self, appointment_id: int):
        """
        Получает заявку по ID.
        """
        result = await self.session.execute(
           
        """
        Получает все заявки специалиста.
        """
        result = await self.session.execute(
            select(Appointment)
            .where(Appointment.specialist_id == specialist_id)
            .options(joinedload(Appointment.client))
        )
        appointments = result.scalars().all()
        logger.info(f"Fetched {len(appointments)} appointments for specialist_id={specialist_id}")
        return appointments

        Увеличивает счетчик завершенных заявок специалиста и обновляет ранг.
        """
        specialist = await self.session.get(Specialist, specialist_id)
        if specialist:
            specialist.completed_appointments += 1
            await self.session.commit()
            await self.update_specialist_rank(specialist_id)  # Update string-based rank
            logger.info(f"Incremented completed_appointments for specialist_id={specialist_id}")
        else:
            logger.error(f"Specialist {specialist_id} not found")

    async def reset_specialist_ranks(self):
        """
        Сбрасывает ранги и счетчик завершенных заявок всех специалистов.
        ""
        specialist = await self.session.get(Specialist, specialist_id)
        if specialist:
            specialist.is_available = is_available
            await self.session.commit()
            logger.info(f"Updated specialist {specialist_id} availability to {is_available}")
            return specialist
        logger.error(f"Specialist {specialist_id} not found")
        return None

    async def add_to_blacklist(self, telegram_id: str, reason: str, duration_days: int):
        """
        Добавляет пользователя в черный список.
        """
        blocked_until = datetime.now(tz=config.TIMEZONE) + timedelta(days=duration_days)
        blacklist_entry = Blacklist(
            telegram_id=telegram_id,
            reason=reason,
            bl
        logger.info(f"Fetched total clients: {total}")
        return total

    async def get_approved_appointments_count(self):
        """
        Получает количество одобренных заявок.
        """
        result = await self.session.execute(select(Appointment).where(Appointment.status == AppointmentStatus.APPROVED))
        count = len(result.scalars().all())
        logger.info(f"Fetched approved appointments count: {count}")
        return count

    async def remove_invalid_specialists(self):
        """
        Удаляет специалистов без соответствующего пользователя.
        """
        result = await self.session.execute(
            select(Specialist).outerjoin(User, Specialist.user_id == User.telegram_id)
            .where(User.telegram_id.is_(None))
        )
        invalid_specialists = result.scalars().all()
        for specialist in invalid_specialists:
            await self.session.delete(specialist)
        await self.session.commit()
        
        notification = NotificationSent(
            appointment_id=appointment_id,
            reminder_type=reminder_type,
            sent_at=datetime.now(tz=config.TIMEZONE)
        )
        self.session.add(notification)
        await self.session.commit()
        logger.info(f"Created notification for appointment_id={appointment_id}, type={reminder_type}")
        return notification

    async def get_sent_notifications(self, appointment_id: int):
        """
        Получает все отправленные уведомления для заявки.
        """
        result = await self.session.execute(
            select(NotificationSent)
     
        report = SpecialistReport(specialist_id=specialist_id, report_text=report_text)
        self.session.add(report)
        await self.session.commit()
        logger.info(f"Created report for specialist_id={specialist_id}")
        return report

    async def update_client_rating(self, client_id: int, rating: int):
        """
            .where(
                Appointment.status == AppointmentStatus.APPROVED,
                Appointment.scheduled_time >= now
            )
            .options(joinedload(Appointment.client).joinedload(Client.user), joinedload(Appointment.specialist))
            .order_by(Appointment.scheduled_time)
        )
        appointments = result.scalars().all()
        logger.info(f"Fetched {len(appointments)} future approved appointments")
        return appointments
