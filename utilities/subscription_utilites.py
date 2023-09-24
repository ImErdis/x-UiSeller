from telegram import InlineKeyboardButton


def create_keyboard(remaining_traffic, remaining_seconds, subscription):
    """Generate inline keyboard for the given subscription."""
    return [
        [InlineKeyboardButton(header, callback_data='notabutton') for header in
         ['⚡️ حجم باقی‌مانده', '⏳ زمان باقی‌مانده']],
        [InlineKeyboardButton(value, callback_data='notabutton') for value in
         [f'{remaining_traffic} گیگابایت', f'{format_time(remaining_seconds)}']],
        [InlineKeyboardButton('🔗 لینک اتصال',
                              callback_data=f'connect_url-subscriptions{{{subscription.uuid_decoded}}}')],
        [InlineKeyboardButton("🖥️ بازگشت به پنل", callback_data="menu")]
    ]


def format_time(remaining_seconds):
    # Constants
    SECONDS_PER_MINUTE = 60
    MINUTES_PER_HOUR = 60
    HOURS_PER_DAY = 24
    DAYS_PER_MONTH = 30  # Taking an average value

    # Calculate Minutes + Seconds
    if remaining_seconds < SECONDS_PER_MINUTE * MINUTES_PER_HOUR:
        minutes = remaining_seconds // SECONDS_PER_MINUTE
        seconds = remaining_seconds % SECONDS_PER_MINUTE
        return f"{minutes} دقیقه و {seconds} ثانیه"

    # Calculate Hours + Minutes
    if remaining_seconds < SECONDS_PER_MINUTE * MINUTES_PER_HOUR * HOURS_PER_DAY:
        hours = remaining_seconds // (SECONDS_PER_MINUTE * MINUTES_PER_HOUR)
        minutes = (remaining_seconds % (SECONDS_PER_MINUTE * MINUTES_PER_HOUR)) // SECONDS_PER_MINUTE
        return f"{hours} ساعت و {minutes} دقیقه"

    # Calculate Days + Hours
    if remaining_seconds < SECONDS_PER_MINUTE * MINUTES_PER_HOUR * HOURS_PER_DAY * DAYS_PER_MONTH:
        days = remaining_seconds // (SECONDS_PER_MINUTE * MINUTES_PER_HOUR * HOURS_PER_DAY)
        hours = (remaining_seconds % (SECONDS_PER_MINUTE * MINUTES_PER_HOUR * HOURS_PER_DAY)) // (
                    SECONDS_PER_MINUTE * MINUTES_PER_HOUR)
        return f"{days} روز و {hours} ساعت"

    # Calculate Months + Days
    months = remaining_seconds // (SECONDS_PER_MINUTE * MINUTES_PER_HOUR * HOURS_PER_DAY * DAYS_PER_MONTH)
    days = (remaining_seconds % (SECONDS_PER_MINUTE * MINUTES_PER_HOUR * HOURS_PER_DAY * DAYS_PER_MONTH)) // (
                SECONDS_PER_MINUTE * MINUTES_PER_HOUR * HOURS_PER_DAY)
    return f"{months} ماه و {days} روز"
