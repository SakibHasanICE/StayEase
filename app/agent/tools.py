import asyncio
from datetime import date
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from sqlalchemy import select, and_, or_, not_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import AsyncSessionLocal
from app.config.models import Listing, Booking


# ── Input Schemas ────────────────────────────────────────────────────────────

class SearchInput(BaseModel):
    location:  str  = Field(..., description="City or area name in Bangladesh")
    check_in:  date = Field(..., description="Check-in date YYYY-MM-DD")
    check_out: date = Field(..., description="Check-out date YYYY-MM-DD")
    guests:    int  = Field(..., ge=1, description="Number of guests")


class DetailsInput(BaseModel):
    listing_id: int = Field(..., description="Unique listing ID")


class BookingInput(BaseModel):
    listing_id:  int  = Field(..., description="Property to book")
    guest_name:  str  = Field(..., description="Full name of the guest")
    guest_phone: str  = Field(..., description="Guest contact number")
    check_in:    date = Field(..., description="Check-in date YYYY-MM-DD")
    check_out:   date = Field(..., description="Check-out date YYYY-MM-DD")
    guests:      int  = Field(..., ge=1, description="Number of guests")


# ── Async DB helpers (tools are sync; we run them in the event loop) ─────────

async def _search_db(location: str, check_in: date, check_out: date, guests: int) -> list[dict]:
    async with AsyncSessionLocal() as db:
        # Listings that overlap with requested dates are booked — exclude them
        booked_ids_stmt = select(Booking.listing_id).where(
            and_(
                Booking.check_in  < check_out,
                Booking.check_out > check_in,
                Booking.status    == "confirmed",
            )
        )
        stmt = (
            select(Listing)
            .where(
                and_(
                    Listing.location.ilike(f"%{location}%"),
                    Listing.max_guests >= guests,
                    Listing.is_active  == True,
                    ~Listing.id.in_(booked_ids_stmt),
                )
            )
        )
        rows = (await db.execute(stmt)).scalars().all()
        return [
            {
                "id":              r.id,
                "name":            r.name,
                "location":        r.location,
                "price_per_night": float(r.price_per_night),
                "max_guests":      r.max_guests,
                "amenities":       r.amenities or [],
            }
            for r in rows
        ]


async def _details_db(listing_id: int) -> dict | None:
    async with AsyncSessionLocal() as db:
        row = await db.get(Listing, listing_id)
        if not row:
            return None
        return {
            "id":                  row.id,
            "name":                row.name,
            "location":            row.location,
            "description":         row.description,
            "address":             row.address,
            "price_per_night":     float(row.price_per_night),
            "max_guests":          row.max_guests,
            "amenities":           row.amenities or [],
            "cancellation_policy": row.cancellation_policy,
            "photos_url":          row.photos_url,
        }


async def _create_booking_db(
    listing_id: int, guest_name: str, guest_phone: str,
    check_in: date, check_out: date, guests: int,
) -> dict:
    async with AsyncSessionLocal() as db:
        listing = await db.get(Listing, listing_id)
        if not listing:
            raise ValueError(f"Listing {listing_id} not found.")

        nights      = (check_out - check_in).days
        total_price = nights * float(listing.price_per_night)

        booking = Booking(
            listing_id=listing_id,
            guest_name=guest_name,
            guest_phone=guest_phone,
            check_in=check_in,
            check_out=check_out,
            guests=guests,
            total_price=total_price,
            status="confirmed",
        )
        db.add(booking)
        await db.commit()
        await db.refresh(booking)

        return {
            "booking_id":     booking.id,
            "listing_id":     listing_id,
            "guest_name":     guest_name,
            "check_in":       str(check_in),
            "check_out":      str(check_out),
            "nights":         nights,
            "total_price_bdt": total_price,
            "status":         "confirmed",
            "message":        f"Booking confirmed! Total: ৳{total_price:,.0f} for {nights} night(s).",
        }


# ── Tool definitions (sync wrappers around async helpers) ────────────────────

@tool("search_available_properties", args_schema=SearchInput)
def search_available_properties(location: str, check_in: date, check_out: date, guests: int) -> list[dict]:
    """Search available properties by location, dates, and guest count. Returns matching listings in BDT."""
    return asyncio.get_event_loop().run_until_complete(
        _search_db(location, check_in, check_out, guests)
    )


@tool("get_listing_details", args_schema=DetailsInput)
def get_listing_details(listing_id: int) -> dict:
    """Fetch full details for a specific property listing including address, amenities, and cancellation policy."""
    result = asyncio.get_event_loop().run_until_complete(_details_db(listing_id))
    if not result:
        return {"error": f"Listing {listing_id} not found."}
    return result


@tool("create_booking", args_schema=BookingInput)
def create_booking(
    listing_id: int, guest_name: str, guest_phone: str,
    check_in: date, check_out: date, guests: int,
) -> dict:
    """Create a confirmed booking. Returns booking ID, total price in BDT, and confirmation message."""
    return asyncio.get_event_loop().run_until_complete(
        _create_booking_db(listing_id, guest_name, guest_phone, check_in, check_out, guests)
    )


TOOLS = [search_available_properties, get_listing_details, create_booking]