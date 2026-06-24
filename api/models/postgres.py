from pydantic import BaseModel


class Account(BaseModel):

    account_id: int

    customer_name: str

    email: str


class Invoice(BaseModel):

    invoice_id: int

    account_id: int

    amount: float

    status: str