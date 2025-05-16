from aiogram.fsm.state import State, StatesGroup

class ClientStates(StatesGroup):
    """Состояния FSM для клиентов."""
    await_codeword = State()
    registration = State()
    city = State()
    phone = State()
    choose_type = State()
    choose_part = State()
    choose_complex = State()
    enter_date = State()
    collecting_reason = State()
    reject_reason = State()
    cancel_appointment = State()
    cancel_reason = State()

class AdminStates(StatesGroup):
    """Состояния FSM для администратора."""
    select_time = State()
    select_specialist = State()
    blacklist_management = State()
    reject_reason = State()
    add_specialist = State()
    adding_specialist_details = State()
    removing_specialist = State()
    adding_to_blacklist = State()
    adding_to_blacklist_details = State()
    removing_from_blacklist = State()
    view_appointments = State()
    export_data = State()

class AdminStates(StatesGroup):
    view_appointments = State()
    blacklist_management = State()
    adding_to_blacklist = State()
    adding_to_blacklist_details = State()
    export_data = State()
    select_specialist = State()
    select_time = State()
    reject_reason = State()
    add_specialist = State()
    adding_specialist_details = State()
    removing_specialist = State()
    view_specialists = State()
    view_specialist_appointments = State()
    reassign_specialist = State()

class SpecialistStates(StatesGroup):
    """Состояния FSM для специалистов."""
    change_availability = State()
    submit_report = State()
    submit_report_text = State()
    cancel_reason = State()