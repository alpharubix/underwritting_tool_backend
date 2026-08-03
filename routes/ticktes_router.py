from fastapi import APIRouter
from fastapi import Request
from controller.tickets_controller.ticket_controller import raise_ticket,get_user_ticket_history

ticket_router = APIRouter(prefix="/v1/ticket", tags=["Ticket"])


@ticket_router.post("/create", tags=["Ticket"])
async def create_ticket(req:Request):
    return await raise_ticket(request=req)

@ticket_router.get("/history", tags=["Tickets"])
async def get_tickets(req:Request):
  return await get_user_ticket_history(req)
