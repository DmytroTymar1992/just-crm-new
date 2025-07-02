# chats/templatetags/telegram_date.py
from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

WEEKDAYS_UA = {
    0: 'Понеділок',
    1: 'Вівторок',
    2: 'Середа',
    3: 'Четвер',
    4: "П’ятниця",
    5: 'Субота',
    6: 'Неділя',
}

# Скорочені назви місяців українською з крапкою
MONTHS_SHORT_UA = {
    1: 'січ.',
    2: 'лют.',
    3: 'бер.',
    4: 'квіт.',
    5: 'тра.',
    6: 'черв.',
    7: 'лип.',
    8: 'серп.',
    9: 'вер.',
    10: 'жов.',
    11: 'лист.',
    12: 'груд.',
}

@register.filter
def telegram_date(day):
    """
    Перетворює datetime.date на:
      - «Сьогодні» (якщо today)
      - «Вчора» (якщо yesterday)
      - назву дня тижня (якщо в межах поточного тижня)
      - 'DD MMM.' (наприклад, '05 бер.') — якщо той же рік
      - 'DD MMM. YYYY' (наприклад, '05 бер. 2024') — якщо інший рік
    """
    today = timezone.localtime(timezone.now()).date()
    if day == today:
        return 'Сьогодні'
    if day == today - timedelta(days=1):
        return 'Вчора'

    start_of_week = today - timedelta(days=today.weekday())
    if day >= start_of_week:
        return WEEKDAYS_UA[day.weekday()]

    month_short = MONTHS_SHORT_UA[day.month]
    if day.year == today.year:
        return f"{day.day:02d} {month_short}"
    return f"{day.day:02d} {month_short} {day.year}"
