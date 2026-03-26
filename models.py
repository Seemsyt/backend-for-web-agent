from pydantic import BaseModel, EmailStr, Field, model_validator


class CreateTodo(BaseModel):
    thread_id:str 
    class Config:
        from_attributes = True

class LoginSchema(BaseModel):
    email:EmailStr
    password:str = Field(...,min_length=8,max_length=120)

    class Config:
        from_attributes = True

class RegisterSchema(BaseModel):
    email:EmailStr = Field(...,max_length=119)
    username:str = Field(...,min_length=3,max_length=120)
    password:str = Field(...,min_length=8,max_length=120)
    confirm_password:str = Field(...,min_length=6,max_length=120)

    class Config:
        from_attributes = True

    @model_validator(mode='after')
    def check_password(self):
        if (self.password == self.confirm_password):
            return self
        raise ValueError("confirm password do not match ")
    
class AuthUserSchema(BaseModel):
    id:int
    username:str
    email:EmailStr