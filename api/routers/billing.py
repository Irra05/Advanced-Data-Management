from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from datetime import date

from db.postgres import get_pool

router = APIRouter(
    prefix="/billing",
    tags=["Billing"]
)


@router.get("/account/{premise_id}")
async def get_account(premise_id: int):

    pool = await get_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT *
            FROM consumer_accounts
            WHERE account_id = $1
            """,
            premise_id
        )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    return dict(row)


class InvoiceCreate(BaseModel):
    premise_id: str
    billing_period_start: date
    billing_period_end: date
    consumption_kwh: float
    base_charge: float
    energy_charge: float
    regulatory_surcharge: float
    time_of_use_adjustment: float
    
@router.post("/invoice", status_code=201)
async def create_invoice(data: InvoiceCreate):

    total = round(
        data.base_charge +
        data.energy_charge +
        data.regulatory_surcharge +
        data.time_of_use_adjustment,
        2
    )

    pool = await get_pool()

    async with pool.acquire() as conn:
        # ACID transaction — if any step fails, everything will be rolled back
        async with conn.transaction():

            account = await conn.fetchrow(
                "SELECT account_id FROM consumer_accounts WHERE premise_id = $1",
                data.premise_id
            )

            if account is None:
                raise HTTPException(status_code=404, detail="Premise not found")

            invoice = await conn.fetchrow(
                """
                INSERT INTO invoices (
                    account_id, billing_period_start, billing_period_end,
                    consumption_kwh, base_charge, energy_charge,
                    regulatory_surcharge, time_of_use_adjustment, total_amount, status
                )
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,'PENDING')
                RETURNING invoice_id, total_amount, status
                """,
                account["account_id"],
                data.billing_period_start,
                data.billing_period_end,
                data.consumption_kwh,
                data.base_charge,
                data.energy_charge,
                data.regulatory_surcharge,
                data.time_of_use_adjustment,
                total
            )

    return {
        "invoice_id": invoice["invoice_id"],
        "premise_id": data.premise_id,
        "total_amount": invoice["total_amount"],
        "status": invoice["status"]
    }


#!  Is this endpoint needed?

@router.get("/invoice/{invoice_id}")
async def get_invoice(invoice_id: int):

    pool = await get_pool()

    async with pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            SELECT *
            FROM invoices
            WHERE invoice_id = $1
            """,
            invoice_id
        )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Invoice not found"
        )

    return dict(row)