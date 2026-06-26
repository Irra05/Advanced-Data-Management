from fastapi import APIRouter, HTTPException

from db.postgres import get_pool

router = APIRouter(
    prefix="/billing",
    tags=["Billing"]
)


@router.get("/account/{account_id}")
async def get_account(account_id: int):

    pool = await get_pool()

    async with pool.acquire() as conn:

        row = await conn.fetchrow(
            """
            SELECT *
            FROM consumer_accounts
            WHERE account_id = $1
            """,
            account_id
        )

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Account not found"
        )

    return dict(row)


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