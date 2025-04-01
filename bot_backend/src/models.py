import enum
from datetime import datetime
from sqlalchemy import ForeignKey, Text, BigInteger, DateTime, Enum, Column, func, Integer
from sqlalchemy.orm import Mapped, mapped_column, declarative_base, relationship
from sqlalchemy.dialects.postgresql import ARRAY



Base = declarative_base()


class MediaType(enum.Enum):
    AUDIO = "audio"
    GIF = "gif"
    PHOTO = "photo"
    VIDEO = "video"
    VOICE = "voice"



class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    saved_collections: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), server_default="{}")
    created_memes: Mapped[list["Meme"]] = relationship()
    is_banned: Mapped[bool] = mapped_column(default=False)
    last_upload_date: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"User(telegram_id={self.telegram_id}, is_banned={self.is_banned}, last_upload_date={self.last_upload_date}"


class Meme(Base):
    __tablename__ = "memes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    uploader_telegram_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    creator: Mapped["User"] = relationship(back_populates="created_memes")
    duration: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(BigInteger, default=0)
    telegram_media_id: Mapped[str]
    title: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType, values_callable=lambda obj: [e.value for e in obj]))
    is_public: Mapped[bool]


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    creator_telegram_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    meme_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), server_default="{}")
    likes: Mapped[int] = mapped_column(BigInteger)
    users_amount: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    is_public: Mapped[bool]
