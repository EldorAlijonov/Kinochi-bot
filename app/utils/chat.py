from aiogram import types


def extract_forwarded_chat(message: types.Message):
    if message.forward_origin and hasattr(message.forward_origin, "chat"):
        return message.forward_origin.chat

    return message.forward_from_chat


def extract_forwarded_chat_id(message: types.Message) -> int | None:
    chat = extract_forwarded_chat(message)
    return chat.id if chat else None


def get_chat_title(chat, fallback: str) -> str:
    title = getattr(chat, "title", None)
    return (title or fallback).strip()
