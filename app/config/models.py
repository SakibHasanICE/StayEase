from datetime import date, datetime
from sqlalchemy import String, Integer, Numeric, Date, Text, Boolean, ForeignKey, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.config.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id:              Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:            Mapped[str]   = mapped_column(String(200), nullable=False)
    location:        Mapped[str]   = mapped_column(String(200), nullable=False, index=True)
    description:     Mapped[str]   = mapped_column(Text, nullable=True)
    address:         Mapped[str]   = mapped_column(Text, nullable=True)
    price_per_night: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    max_guests:      Mapped[int]   = mapped_column(Integer, nullable=False)
    amenities:       Mapped[list]  = mapped_column(ARRAY(String), default=list)
    photos_url:      Mapped[str]   = mapped_column(String(500), nullable=True)
    cancellation_policy: Mapped[str] = mapped_column(Text, nullable=True)
    is_active:       Mapped[bool]  = mapped_column(Boolean, default=True)
    created_at:      Mapped[datetime] = mapped_column(default=datetime.utcnow)

    bookings: Mapped[list["Booking"]] = relationship(back_populates="listing")


class Booking(Base):
    __tablename__ = "bookings"

    id:          Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id:  Mapped[int]   = mapped_column(ForeignKey("listings.id"), nullable=False, index=True)
    guest_name:  Mapped[str]   = mapped_column(String(200), nullable=False)
    guest_phone: Mapped[str]   = mapped_column(String(20), nullable=False)
    check_in:    Mapped[date]  = mapped_column(Date, nullable=False)
    check_out:   Mapped[date]  = mapped_column(Date, nullable=False)
    guests:      Mapped[int]   = mapped_column(Integer, nullable=False)
    total_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status:      Mapped[str]   = mapped_column(String(20), default="confirmed")
    created_at:  Mapped[datetime] = mapped_column(default=datetime.utcnow)

    listing: Mapped["Listing"] = relationship(back_populates="bookings")


class Conversation(Base):
    __tablename__ = "conversations"

    id:              Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str]  = mapped_column(String(100), nullable=False, index=True)
    role:            Mapped[str]  = mapped_column(String(20), nullable=False)   # user | assistant
    content:         Mapped[str]  = mapped_column(Text, nullable=False)
    intent:          Mapped[str]  = mapped_column(String(50), nullable=True)
    created_at:      Mapped[datetime] = mapped_column(default=datetime.utcnow)