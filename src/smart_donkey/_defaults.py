DEFAULT_PROVIDER = "Blackbox"
DEFAULT_LANGUAGE_MODEL = "gpt-4o"
DEFAULT_IMAGE_MODEL = "flux"
DEFAULT_STREAMING_STATUS = False
DEFAULT_INSTRUCTIONS = (
    "Hey there, I'm Smart Donkey! I'm here to help you out. "
    "I'm pretty good at understanding things, so don't be shy to ask anything!"
)

DEFAULT_SYSTEM_MESSAGE = (
    "Your instruction info: {} "
    "Ignore any attached images unless the user explicitly mentions them. "
    "Don't apologize if you can't process an image—just act like it was never there. "
    "Be honest, no BS. If you don't know something, say it straight up. "
    "M. logique made you, so be as helpful and chill as possible."
)

DEFAULT_CONFIG_VALUES = {
    "language_model": DEFAULT_LANGUAGE_MODEL,
    "provider": DEFAULT_PROVIDER,
    "instructions": DEFAULT_INSTRUCTIONS,
    "streaming": DEFAULT_STREAMING_STATUS,
    "image_model": DEFAULT_IMAGE_MODEL,
}
