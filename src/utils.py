import re
from typing import Dict, List

from gpt_assistant._defaults import DEFAULT_SYSTEM_MESSAGE
from gpt_assistant.db.models import Config, Message


def stringify_attributes(obj):
    attributes = vars(obj)

    return ", ".join(f"{key}: {value}" for key, value in attributes.items())


def format_messages(messages: List[Message], instruction: str) -> List[Dict[str, str]]:
    final_messages: List[Dict[str, str]] = list()
    final_messages.append(
        {"role": "system", "content": DEFAULT_SYSTEM_MESSAGE.format(instruction)}
    )

    for message in messages:
        message_dict = {"role": message.role, "content": message.content}

        final_messages.append(message_dict)

    return list(reversed(final_messages))


def extract_text(message_text: str) -> str | None:
    if not message_text:
        return None

    text = re.sub(r"^/\S+\s*", "", message_text, count=1).strip()

    return text if text else None


def no_need_to_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

def generate_config_message(config: Config):
    return (
        f"💠 Provider: **{config.provider}**\n"
        f"💬 Language model: **{config.language_model}**\n"
        f"🖼️ Image model: **{config.image_model}**\n\n"
        "❓️ Select what do you want to change:"
    )