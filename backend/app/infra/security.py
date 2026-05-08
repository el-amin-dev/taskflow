from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()

def hash_password (plaintext:str) -> str:
    return _hasher.hash(plaintext)

def verify_password (plaintext:str,hashed:str) -> bool:
    try:
        _hasher.verify(hashed,plaintext) 
        return True
    except VerifyMismatchError:
        return False
