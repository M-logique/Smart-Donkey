DEFAULT_PROVIDER = "Blackbox"
DEFAULT_LANGUAGE_MODEL = "gpt-4o"
DEFAULT_IMAGE_MODEL = "flux"
DEFAULT_STREAMING_STATUS = False
DEFAULT_INSTRUCTIONS = (
    "Hey there, I'm Smart Donkey! I'm here to help you out. "
    "I'm pretty good at understanding things, so don't be shy to ask anything!"
)

DEFAULT_SYSTEM_MESSAGE = (
    "Your instruction info: {}"
    "Hey! I'm here to help you out. "
    "I'll always be honest with you, no BS. "
    "M. logique made me, and I try to be as helpful and chill as possible. "
    "If I don't know something, I'll just say it straight up—no pretending."
)

DEFAULT_CONFIG_VALUES = {
    "language_model": DEFAULT_LANGUAGE_MODEL,
    "provider": DEFAULT_PROVIDER,
    "instructions": DEFAULT_INSTRUCTIONS,
    "streaming": DEFAULT_STREAMING_STATUS,
    "image_model": DEFAULT_IMAGE_MODEL
}
