import random
import string

def generate_otp(length: int = 6) -> str:
    """Generate a random numeric OTP of specified length."""
    return "".join(random.choices(string.digits, k=length))
