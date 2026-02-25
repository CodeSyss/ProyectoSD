from pydantic import BaseModel, EmailStr


class EmailRegistration(BaseModel):
    """Modelo para validar el registro de correo electrónico."""
    email: EmailStr
