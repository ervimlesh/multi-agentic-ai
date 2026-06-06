"""OTP generation, hashing, and delivery."""
import hashlib
import hmac
import secrets

from app.core.config import settings
from app.core.email import send_email


def generate_code() -> str:
    """Return a zero-padded numeric OTP of configured length."""
    upper = 10**settings.OTP_LENGTH
    return str(secrets.randbelow(upper)).zfill(settings.OTP_LENGTH)


def hash_code(code: str) -> str:
    """Keyed SHA-256 hash so stored codes cannot be brute-forced offline."""
    return hmac.new(
        settings.JWT_SECRET_KEY.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_code(code: str, code_hash: str) -> bool:
    return hmac.compare_digest(hash_code(code), code_hash)


async def deliver_otp(email: str, code: str, purpose: str = "login") -> None:
    """Send the OTP to the user's email (patched in tests)."""
    action = "create your account" if purpose == "register" else "sign in"
    subject = f"Your verification code: {code}"
    body = (
        f"Hi,\n\n"
        f"Use this code to {action}:\n\n"
        f"    {code}\n\n"
        f"It expires in {settings.OTP_EXPIRE_MINUTES} minutes. "
        f"If you didn't request this, you can ignore this email.\n\n"
        f"— {settings.PROJECT_NAME}"
    )
    await send_email(email, subject, body)
