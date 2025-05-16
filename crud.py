from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from database.models import User, Client, Specialist, Appointment, Blacklist, Role, AppointmentStatus, NotificationSent
from datetime import datetime, timedelta
from config import config
import logging

logger = logging.getLogger(__name__)


class CRUD:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_user(self, telegram_id: str, role: Role):
        """
        Создает нового пользователя.
        """
        user = User(telegram_id=telegram_id, role=role)
        self.session.add(user)
        await self.session.commit()
        logger.info(f"Created user with telegram_id={telegram_id}, role={role}")
        return user

    async def get_user(self, telegram_id: str):
        """
        Получает пользователя по telegram_id.
        """
        result = await self.session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(joinedload(User.client), joinedload(User.specialist))
        )
        user = result.scalars().first()
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
        """
        result = await self.session.execute(
            select(Client)
            .join(User, Client.user_id == User.telegram_id)
            .where(User.role == Role.CLIENT)
            .options(joinedload(Client.user))
        )
        clients = result.scalars().all()
        logger.info(f"Fetched {len(clients)} clients")
        return clients

    async def create_specialist(self, specialist: Specialist):
        """
        Создает нового специалиста.
        """
        user = await self.get_user(specialist.user_id)
        if not user:
            logger.error(f"User {specialist.user_id} does not exist")
            raise ValueError(f"User {specialist.user_id} must interact with the bot before becoming a specialist.")
        self.session.add(specialist)
        await self.session.commit()
        logger.info(f"Created specialist with user_id={specialist.user_id}, full_name={specialist.full_name}")
        return specialist

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
        """
        result = await self.session.execute(
            select(Specialist)
            .where(Specialist.is_available == True)
            .options(joinedload(Specialist.user))
        )
        specialists = result.scalars().all()
        logger.info(f"Fetched {len(specialists)} available specialists")
        return specialists

    async def get_all_specialists(self):
        """
        Получает всех специалистов.
        """
        result = await self.session.execute(
            select(Specialist)
            .options(joinedload(Specialist.user))
        )
        specialists = result.scalars().all()
        logger.info(f"Fetched {len(specialists)} specialists")
        return specialists

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
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .options(joinedload(Appointment.client).joinedload(Client.user), joinedload(Appointment.specialist))
        )
        appointment = result.scalars().first()
        logger.debug(f"Fetched appointment id={appointment_id}")
        return appointment

    async def get_appointments_by_client(self, client_id: int):
        """
        Получает заявки клиента.
        """
        result = await self.session.execute(
            select(Appointment)
            .where(Appointment.client_id == client_id)
            .options(joinedload(Appointment.specialist))
        )
        appointments = result.scalars().all()
        logger.info(f"Fetched {len(appointments)} appointments for client_id={client_id}")
        return appointments

    async def get_appointments_by_specialist(self, specialist_id: int):
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

    async def get_all_appointments(self):
        """
        Получает все заявки.
        """
        result = await self.session.execute(
            select(Appointment)
            .options(joinedload(Appointment.client), joinedload(Appointment.specialist))
        )
        appointments = result.scalars().all()
        logger.info(f"Fetched {len(appointments)} appointments")
        return appointments

    async def get_appointments_by_status(self, status: AppointmentStatus, options=None):
        """
        Получает заявки по статусу.
        """
        query = select(Appointment).where(Appointment.status == status)
        if options:
            query = query.options(*options)
        result = await self.session.execute(query)
        appointments = result.scalars().all()
        logger.info(f"Fetched {len(appointments)} appointments with status={status}")
        return appointments

    async def increment_specialist_completed_appointments(self, specialist_id: int):
        """
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
        """
        specialists = await self.get_all_specialists()
        for spec in specialists:
            spec.completed_appointments = 0
            spec.rank = "Новобранец"  # Changed to match custom rank
        await self.session.commit()
        logger.info(f"Reset ranks for {len(specialists)} specialists")

    async def toggle_specialist_availability(self, specialist_id: int):
        """
        Переключает статус доступности специалиста.
        """
        specialist = await self.session.get(Specialist, specialist_id)
        if specialist:
            specialist.is_available = not specialist.is_available
            await self.session.commit()
            logger.info(f"Toggled availability for specialist_id={specialist_id} to {specialist.is_available}")
            return specialist.is_available
        logger.error(f"Specialist {specialist_id} not found")
        return None

    async def update_specialist_availability(self, specialist_id: int, is_available: bool):
        """
        Обновляет статус доступности специалиста.
        """
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
            blocked_until=blocked_until
        )
        self.session.add(blacklist_entry)
        await self.session.commit()
        logger.info(f"Added user {telegram_id} to blacklist until {blocked_until}")

    async def is_blacklisted(self, telegram_id: str):
        """
        Проверяет, находится ли пользователь в черном списке.
        """
        result = await self.session.execute(select(Blacklist).where(Blacklist.telegram_id == telegram_id))
        blacklist_entry = result.scalars().first()
        logger.debug(f"Checked blacklist for telegram_id={telegram_id}: {'found' if blacklist_entry else 'not found'}")
        return blacklist_entry

    async def get_blacklist(self):
        """
        Получает всех пользователей в черном списке.
        """
        result = await self.session.execute(select(Blacklist))
        blacklist = result.scalars().all()
        logger.info(f"Fetched {len(blacklist)} blacklist entries")
        return blacklist

    async def get_total_clients(self):
        """
        Получает общее количество клиентов.
        """
        result = await self.session.execute(select(Client))
        total = len(result.scalars().all())
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
        logger.info(f"Removed {len(invalid_specialists)} invalid specialists")
        return len(invalid_specialists)

    async def is_time_occupied(self, proposed_date: datetime, time_str: str):
        """
        Проверяет, занято ли указанное время.
        """
        slot_datetime = datetime.strptime(
            f"{proposed_date.strftime('%Y-%m-%d')} {time_str}",
            "%Y-%m-%d %H:%M"
        ).replace(tzinfo=config.TIMEZONE)
        result = await self.session.execute(
            select(Appointment)
            .where(
                Appointment.scheduled_time == slot_datetime,
                Appointment.status == AppointmentStatus.APPROVED
            )
            .options(joinedload(Appointment.specialist))
        )
        appointment = result.scalars().first()
        logger.debug(f"Checked time slot {slot_datetime}: {'occupied' if appointment else 'free'}")
        return appointment

    async def create_notification_sent(self, appointment_id: int, reminder_type: str):
        """
        Создает запись об отправленном уведомлении.
        """
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
            .where(NotificationSent.appointment_id == appointment_id)
        )
        notifications = result.scalars().all()
        logger.info(f"Fetched {len(notifications)} notifications for appointment_id={appointment_id}")
        return notifications

    async def get_appointments_by_date_range(self, start_date: datetime, end_date: datetime):
        """
        Получает заявки за указанный период.
        """
        result = await self.session.execute(
            select(Appointment)
            .where(Appointment.proposed_date >= start_date)
            .where(Appointment.proposed_date <= end_date)
            .options(joinedload(Appointment.client).joinedload(Client.user), joinedload(Appointment.specialist))
        )
        appointments = result.scalars().all()
        logger.info(f"Fetched {len(appointments)} appointments from {start_date} to {end_date}")
        return appointments

    async def create_specialist_report(self, specialist_id: int, report_text: str):
        """
        Создает отчет специалиста.
        """
        from database.models import SpecialistReport
        report = SpecialistReport(specialist_id=specialist_id, report_text=report_text)
        self.session.add(report)
        await self.session.commit()
        logger.info(f"Created report for specialist_id={specialist_id}")
        return report

    async def update_client_rating(self, client_id: int, rating: int):
        """
        Обновляет рейтинг клиента.
        """
        if not 1 <= rating <= 5:
            logger.warning(f"Invalid rating value: {rating}")
            raise ValueError("Рейтинг должен быть от 1 до 5")
        client = await self.session.get(Client, client_id)
        if not client:
            logger.error(f"Client not found: {client_id}")
            raise ValueError("Клиент не найден")
        client.rating += rating
        client.rating_count += 1
        await self.session.commit()
        logger.info(
            f"Updated rating for client {client_id}: rating={client.rating}, rating_count={client.rating_count}")

    async def update_specialist_rank(self, specialist_id: int):
        """
        Update the specialist's rank based on completed appointments.
        """
        specialist = await self.session.get(Specialist, specialist_id)
        if not specialist:
            logger.error(f"Specialist not found: {specialist_id}")
            raise ValueError("Специалист не найден")

        ranks = [
            "Подстаканник для кофе", "Шлепок майонезный", "Куркума волосатая", "Капрал", "Старший Капрал",
            "Боевая капибара", "Слон", "Рядовой", "Ефрейтор", "Сержант", "Дембель"
        ]
        rank_index = min(specialist.completed_appointments // 7, len(ranks) - 1)
        new_rank = ranks[rank_index]

        if specialist.rank != new_rank:
            specialist.rank = new_rank
            await self.session.commit()
            logger.info(f"Updated rank for specialist {specialist_id} to {new_rank}")
            return new_rank
        return None

    async def get_future_appointments(self):
        """
        Получает все одобренные заявки с будущей датой.
        """
        now = datetime.now(tz=config.TIMEZONE)
        result = await self.session.execute(
            select(Appointment)
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