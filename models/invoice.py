from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Any, Union, Dict

from pydantic import BaseModel, conint, condecimal, Field
from pydantic.v1 import ValidationError


class InvoiceRequest(BaseModel):
    amount: str
    currency: str
    order_id: str
    network: Optional[str] = None
    url_return: Optional[str] = None
    url_success: Optional[str] = None
    url_callback: Optional[str] = None
    is_payment_multiple: Optional[bool] = None
    lifetime: Optional[conint(ge=300, le=43200)] = None
    to_currency: Optional[str] = None
    subtract: Optional[conint(ge=0, le=100)] = None
    accuracy_payment_percent: Optional[condecimal(ge=0, le=5)] = None
    additional_data: Optional[str] = None
    currencies: Optional[List[str]] = None
    except_currencies: Optional[List[str]] = None
    course_source: Optional[str] = None
    from_referral_code: Optional[str] = None
    discount_percent: Optional[conint(ge=-99, le=100)] = None
    is_refresh: Optional[bool] = None

    @staticmethod
    def create_invoice(data: dict) -> "InvoiceRequest":
        try:
            invoice = InvoiceRequest(**data)
            return invoice
        except ValidationError as e:
            print(e.json())
            return None


class CurrencyStructure(BaseModel):
    currency: str
    network: Optional[str]


class ExceptCurrencyStructure(BaseModel):
    currency: str
    network: Optional[str]


class InvoiceResponse(BaseModel):
    uuid: str
    order_id: str
    amount: Decimal = None
    payment_amount: Optional[Decimal] = None
    payer_amount: Optional[Decimal] = None
    discount_percent: Optional[Decimal] = None
    discount: Decimal = None
    payer_currency: Optional[str]
    currency: str
    merchant_amount: Optional[Decimal] = None
    network: Optional[str]
    address: Optional[str]
    from_address: Optional[str] = Field(default=None, alias="from")  # Added alias here
    txid: Optional[str] = None
    payment_status: str
    url: str
    expired_at: int
    status: str
    is_final: bool
    additional_data: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    def model_dump(self, mongo=False, **kwargs) -> dict:
        output = super().model_dump(**kwargs)
        if mongo:
            for key, value in output.items():
                if isinstance(value, Decimal):
                    output[key] = str(value)
        output['_id'] = output['order_id']
        del output['order_id']
        return output

    @classmethod
    def model_validate(
            cls: type[BaseModel],
            obj: Any,
            *,
            strict: Union[bool, None] = None,
            from_attributes: Union[bool, None] = None,
            context: Union[Dict[str, Any], None] = None,
    ) -> 'InvoiceResponse':
        if isinstance(obj, dict):
            if 'order_id' not in obj and '_id' in obj:
                obj['order_id'] = obj['_id']
            if '_id' in obj:
                del obj['_id']
            for key in ["amount", "payment_amount", "payer_amount", "discount_percent", "discount", "merchant_amount"]:
                if key in obj and obj[key] is not None:
                        obj[key] = Decimal(obj[key])
        return super().model_validate(obj, strict=strict, from_attributes=from_attributes, context=context)


class InvoiceResponseWrapper(BaseModel):
    state: int
    result: InvoiceResponse
