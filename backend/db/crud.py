from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
from backend.db.models import User, Conversation, Message
from typing import List, Optional

# --- Users ---

async def get_user(db: AsyncSession, user_id: str) -> Optional[User]:
    result = await db.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()

async def create_user(db: AsyncSession, user_id: str, email: str) -> User:
    db_user = User(id=user_id, email=email)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# --- Conversations ---

async def get_user_conversations(db: AsyncSession, user_id: str) -> List[Conversation]:
    result = await db.execute(
        select(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(desc(Conversation.updated_at))
    )
    return list(result.scalars().all())

async def get_conversation(db: AsyncSession, conversation_id: str, user_id: str) -> Optional[Conversation]:
    result = await db.execute(
        select(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user_id)
    )
    return result.scalar_one_or_none()

async def create_conversation(db: AsyncSession, user_id: str, title: str = "New Chat") -> Conversation:
    db_conv = Conversation(user_id=user_id, title=title)
    db.add(db_conv)
    await db.commit()
    await db.refresh(db_conv)
    return db_conv

async def update_conversation(db: AsyncSession, conversation_id: str, user_id: str, new_title: str) -> Optional[Conversation]:
    conv = await get_conversation(db, conversation_id, user_id)
    if conv:
        conv.title = new_title
        await db.commit()
        await db.refresh(conv)
        return conv
    return None

async def delete_conversation(db: AsyncSession, conversation_id: str, user_id: str) -> bool:
    conv = await get_conversation(db, conversation_id, user_id)
    if conv:
        await db.delete(conv)
        await db.commit()
        return True
    return False

# --- Messages ---

async def get_conversation_messages(db: AsyncSession, conversation_id: str) -> List[Message]:
    result = await db.execute(
        select(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())

async def add_message(db: AsyncSession, conversation_id: str, role: str, content: str, metadata: dict = None) -> Message:
    db_msg = Message(conversation_id=conversation_id, role=role, content=content, metadata_json=metadata)
    db.add(db_msg)
    
    # Touch the conversation updated_at
    conv_result = await db.execute(select(Conversation).filter(Conversation.id == conversation_id))
    conv = conv_result.scalar_one_or_none()
    if conv:
        from datetime import datetime
        import pytz
        conv.updated_at = datetime.now(pytz.utc)
        
    await db.commit()
    await db.refresh(db_msg)
    return db_msg
