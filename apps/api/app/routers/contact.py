"""Public contact form -- no auth, delivers to settings.contact_email
server-side so the address is never exposed to the frontend."""

from fastapi import APIRouter, status
from pydantic import BaseModel, EmailStr, Field

from app.config import settings
from app.email import send_email

router = APIRouter(prefix="/api/v1/contact", tags=["contact"])


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    message: str = Field(min_length=1, max_length=5000)


@router.post("", status_code=status.HTTP_200_OK, summary="Submit the public contact form")
async def submit_contact(request: ContactRequest) -> dict:
    body = f"From: {request.name} <{request.email}>\n\n{request.message}"
    await send_email(settings.contact_email, f"ScopeWise contact form: {request.name}", body)
    return {"message": "Thanks -- we'll get back to you soon."}
