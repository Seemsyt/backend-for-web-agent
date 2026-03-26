from sqlalchemy.orm import mapped_column , Mapped,relationship
from sqlalchemy import Integer,String,VARCHAR,ForeignKey,DateTime
from .db import Base
from datetime import datetime,timezone
class UserSchema(Base):
    __tablename__ = 'Users'
    id:Mapped[int] = mapped_column(Integer,index=True,autoincrement=True,primary_key=True,unique=True)
    username:Mapped[str] = mapped_column(VARCHAR(100),nullable=False,unique=True)
    email:Mapped[str] = mapped_column(String,nullable=False,unique=True)
    password:Mapped[str] = mapped_column(String,nullable=False)
    threads:Mapped[list["ThreadShema"]] = relationship("ThreadShema")
    created_at:Mapped[datetime] = mapped_column(DateTime,default=datetime.now(timezone.utc))
    updated_at:Mapped[datetime] = mapped_column(DateTime,default=datetime.now(timezone.utc),onupdate=datetime.now(timezone.utc))

class ThreadShema(Base):
    __tablename__ = "Chats"
    id:Mapped[str] = mapped_column(String,primary_key=True,unique=True)
    user:Mapped[int] = mapped_column(Integer,ForeignKey("Users.id",ondelete='CASCADE'))
    created_at:Mapped[datetime] = mapped_column(DateTime,default=datetime.now(timezone.utc))
    updated_at:Mapped[datetime] = mapped_column(DateTime,default=datetime.now(timezone.utc),onupdate=datetime.now(timezone.utc))
    
