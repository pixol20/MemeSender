import enum
from datetime import datetime
from sqlalchemy import ForeignKey, Text, BigInteger, DateTime, Enum, Column, func, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, declarative_base, relationship
from sqlalchemy.dialects.postgresql import ARRAY



Base = declarative_base()


class MediaType(enum.Enum):
    AUDIO = "audio"
    GIF = "gif"
    PHOTO = "photo"
    VIDEO = "video"
    VOICE = "voice"


class UserLikedMemes(Base):
    __tablename__ = "user_liked_memes"

    id = Column(BigInteger, primary_key=True)
    user_telegram_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    meme_id: Mapped[int] = mapped_column(ForeignKey("memes.id"))


class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    saved_collections: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), server_default="{}")
    liked_memes: Mapped[list["Meme"]] = relationship("Meme", secondary=UserLikedMemes)
    created_memes: Mapped[list["Meme"]] = relationship()
    created_collections: Mapped[list["Collection"]] = relationship()
    is_banned: Mapped[bool] = mapped_column(default=False)
    last_upload_date: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"User(telegram_id={self.telegram_id}, is_banned={self.is_banned}, last_upload_date={self.last_upload_date}"


class Meme(Base):
    __tablename__ = "memes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    creator_telegram_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    creator: Mapped["User"] = relationship(back_populates="created_memes")
    liked_users: Mapped[list["User"]] = relationship("User", secondary=UserLikedMemes)
    duration: Mapped[int] = mapped_column(Integer, default=0)
    telegram_media_id: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    media_type: Mapped[MediaType] = mapped_column(Enum(MediaType, name="media_type", values_callable=lambda obj: [e.value for e in obj]))
    is_public: Mapped[bool]

    __table_args__ = (
        Index(
            'pgroonga_memes_titles_index',
            'title',
            postgresql_using='pgroonga',
            postgresql_with={'normalizers': '\'NormalizerNFKC150("remove_symbol", true)\''}
        ),
        Index(
            'pgroonga_memes_tags_index',
            'tags',
            postgresql_using='pgroonga',
            postgresql_with={'normalizers': '\'NormalizerNFKC150("remove_symbol", true)\''}
        )
    )

    def __repr__(self):
        return f"Meme(title: {self.title}, creator: {self.creator}), public: {self.is_public}"


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    creator_telegram_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    creator: Mapped["User"] = relationship(back_populates="created_collections")
    meme_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), server_default="{}")
    likes: Mapped[int] = mapped_column(BigInteger)
    users_amount: Mapped[int] = mapped_column(BigInteger)
    title: Mapped[str] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    is_public: Mapped[bool]

    __table_args__ = (
        Index(
            'pgroonga_collections_titles_index',
            'title',
            postgresql_using='pgroonga',
            postgresql_with={'normalizers': '\'NormalizerNFKC150("remove_symbol", true)\''}
        ),
        Index(
            'pgroonga_collections_tags_index',
            'tags',
            postgresql_using='pgroonga',
            postgresql_with={'normalizers': '\'NormalizerNFKC150("remove_symbol", true)\''}
        )
    )

