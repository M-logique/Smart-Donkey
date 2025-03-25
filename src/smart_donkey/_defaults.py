DEFAULT_PROVIDER = "Blackbox"
DEFAULT_MODEL = "gpt-4o"
DEFAULT_STREAMING_STATUS = False
DEFAULT_INSTRUCTIONS = (
    "Hey there, I'm Smart Donkey! I'm here to help you out. "
    "I'm pretty good at understanding things, so don't be shy to ask anything!"
)

DEFAULT_SYSTEM_MESSAGE = (
    "Your instruction info: {}"
    "You are a helpful assistant. "
    "You always tell the truth. "
    "M. logique developed you. "
    "If you don't know the answer to a question, you truthfully admit that you don't know."
)

DEFAULT_CONFIG_VALUES = {
    "model": DEFAULT_MODEL,
    "provider": DEFAULT_PROVIDER,
    "instructions": DEFAULT_INSTRUCTIONS,
    "streaming": DEFAULT_STREAMING_STATUS
}
