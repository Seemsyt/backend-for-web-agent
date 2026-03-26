from pwdlib import PasswordHash
import jwt
from datetime import timedelta,datetime,timezone
from dotenv import load_dotenv
load_dotenv()
from os import getenv
def hash_password(password:str):
    paswword_hash = PasswordHash.recommended()
    return paswword_hash.hash(password)

def verify_password(password:str,hash_password:str):
    password_hash = PasswordHash.recommended()
    return password_hash.verify(password,hash_password)

def create_acces_token(data:dict,expires_in:int=30):
    to_encode = data.copy()
    expires = datetime.now(timezone.utc) + timedelta(minutes=int(getenv("ACCES_TOKEN_EXPIRE", 30)))
    to_encode.update({"exp":expires})
    encode_jwt = jwt.encode(to_encode,getenv("SECRET_KEY"),algorithm=getenv("ALGORITHEM"))

    return encode_jwt

def decode_acces_token(token:str)->dict:
    try:
        payload = jwt.decode(
            token,
            getenv("SECRET_KEY"),
            algorithms=[getenv("ALGORITHEM")]
        )
        return payload
    except jwt.ExpiredSignatureError:
        print("❌ Token expired")
        raise
    except jwt.InvalidTokenError as e:
        print(f"❌ Invalid token: {str(e)}")
        raise
    except Exception as e:
        print(f"❌ Token decode failed: {str(e)}")
        raise