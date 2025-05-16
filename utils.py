import csv
import io
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from database.crud import CRUD
from config import config


async def export_appointments_to_csv(session: AsyncSession, period: str) -> str:
    """
    Export appointments to CSV format for a given period.

    Args:
        session (AsyncSession): SQLAlchemy async session for database queries.
        period (str): Period for filtering appointments ('1week', '2weeks', '1month').

    Returns:
        str: CSV content as a string.
    """
    crud = CRUD(session)

    # Determine the start date based on the period
    end_date = datetime.now(tz=config.TIMEZONE)
    if period == "1week":
        start_date = end_date - timedelta(days=7)
    elif period == "2weeks":
        start_date = end_date - timedelta(days=14)
    elif period == "1month":
        start_date = end_date - timedelta(days=30)
    else:
        start_date = end_date - timedelta(days=30)  # Default to 1 month

    # Fetch all appointments
    appointments = await crud.get_all_appointments()

    # Filter appointments by date
    filtered_appointments = [
        app for app in appointments
        if start_date <= app.proposed_date.astimezone(config.TIMEZONE) <= end_date
    ]

    # Prepare CSV output
    output = io.StringIO()
    writer = csv.writer(output, lineterminator='\n')

    # Write header
    writer.writerow([
        "ID",
        "Client Name",
        "Client Phone",
        "Specialist Name",
        "Proposed Date",
        "Scheduled Time",
        "Status",
        "Reason",
        "Reject Reason"
    ])

    # Write appointment data
    for app in filtered_appointments:
        proposed_date = app.proposed_date.astimezone(config.TIMEZONE).strftime("%d.%m.%Y")
        scheduled_time = (
            app.scheduled_time.astimezone(config.TIMEZONE).strftime("%H:%M")
            if app.scheduled_time else "Not set"
        )
        specialist_name = app.specialist.full_name if app.specialist else "Not assigned"
        reject_reason = app.reject_reason if app.reject_reason else ""

        writer.writerow([
            app.id,
            app.client.full_name,
            app.client.phone,
            specialist_name,
            proposed_date,
            scheduled_time,
            app.status.value,
            app.reason,
            reject_reason
        ])

    return output.getvalue()