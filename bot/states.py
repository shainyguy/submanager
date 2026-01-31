from aiogram.fsm.state import State, StatesGroup

class AddSubscription(StatesGroup):
    """Состояния добавления подписки"""
    choosing_category = State()
    choosing_service = State()
    entering_name = State()
    entering_price = State()
    choosing_cycle = State()
    entering_start_date = State()
    entering_trial_end = State()
    confirming = State()

class EditSubscription(StatesGroup):
    """Состояния редактирования подписки"""
    choosing_field = State()
    entering_value = State()

class CustomSubscription(StatesGroup):
    """Добавление своей подписки"""
    entering_name = State()
    entering_price = State()
    choosing_cycle = State()
    choosing_category = State()
    entering_start_date = State()
    is_trial = State()
    entering_trial_end = State()

class SearchSubscription(StatesGroup):
    """Поиск подписки"""
    entering_query = State()

class AddTrial(StatesGroup):
    """Добавление триала"""
    choosing_service = State()
    entering_name = State()
    entering_trial_end = State()
    entering_price_after = State()