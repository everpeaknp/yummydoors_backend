from datetime import datetime

from pydantic import BaseModel, ConfigDict, model_validator


class RiderWalletResponse(BaseModel):
    riderUserId: int
    riderName: str | None = None
    balance: float
    canAcceptOffers: bool

    model_config = ConfigDict(from_attributes=True)


class RiderWalletTransactionResponse(BaseModel):
    id: int
    kind: str
    amount: float
    balanceAfter: float
    note: str | None = None
    orderId: int | None = None
    createdAt: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminWalletAdjustRequest(BaseModel):
    # Positive = credit (rider paid us, e.g. via WhatsApp). Negative =
    # debit (correcting a mistaken credit, manual commission recovery,
    # etc). A note is required for a decrement specifically, since taking
    # money away from a rider's balance needs a reason on record.
    amount: float
    note: str | None = None

    @model_validator(mode="after")
    def _validate_amount_and_note(self) -> "AdminWalletAdjustRequest":
        if self.amount == 0:
            raise ValueError("Amount must not be zero.")
        if self.amount < 0 and not (self.note and self.note.strip()):
            raise ValueError("A note is required when decrementing a rider's wallet balance.")
        return self
