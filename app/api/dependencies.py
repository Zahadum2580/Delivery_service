from uuid import uuid4
from fastapi import Request


async def get_or_create_session_id(request: Request) -> str:
    """
    Возвращает session_id из cookie, либо создаёт новый.
    Если создаётся новый — он сохраняется в request.state.new_session_id,
    чтобы роутер мог позже выставить cookie в ответе.
    """
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid4())
        request.state.new_session_id = session_id
    return session_id