from sqlalchemy import Column, Integer, String, Text
from database import Base

class ChatMemory(Base):
    __tablename__ = "chat_memory"
    id = Column(Integer, primary_key=True, index=True)
    user_input = Column(Text, nullable=False)
    agent_reply = Column(Text, nullable=False)
    tool_used = Column(String, nullable=True)