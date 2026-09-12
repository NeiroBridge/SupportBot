from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def mode_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Новая заявка / диагностика",
                    callback_data="mode:lead",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Поддержка по проекту",
                    callback_data="mode:support",
                )
            ],
        ]
    )
