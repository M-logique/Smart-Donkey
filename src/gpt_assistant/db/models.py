from enum import Enum as PyEnum
from typing import List, Tuple

from sqlalchemy import (JSON, TIMESTAMP, BigInteger, Boolean, Enum, ForeignKey,
                        Text, UniqueConstraint, func)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__: Tuple[str, ...] = (
    "Base",
    "Message",
    "ImageGeneration",
    "Config",
    "User",
    "Chat",
)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class Message(Base):
    __tablename__ = "messages"

    _id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.chat_id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    file_hash: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped["TIMESTAMP"] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )


class ImageGeneration(Base):
    __tablename__ = "image_generations"

    _id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.chat_id", ondelete="CASCADE"), nullable=False
    )
    input_file_hash: Mapped[str] = mapped_column(Text, nullable=True)
    output_file_hashes: Mapped[List[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped["TIMESTAMP"] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )


class Config(Base):
    __tablename__ = "config"
    __table_args__ = (UniqueConstraint("chat_id", "user_id"),)

    _id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.chat_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False
    )
    language_model: Mapped[str] = mapped_column(Text, nullable=False)
    image_model: Mapped[str] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=True)
    streaming: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped["TIMESTAMP"] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )


class User(Base):
    __tablename__ = "users"

    _id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    created_at: Mapped["TIMESTAMP"] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )


class Chat(Base):
    __tablename__ = "chats"

    _id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    created_at: Mapped["TIMESTAMP"] = mapped_column(
        TIMESTAMP, server_default=func.now()
    )
