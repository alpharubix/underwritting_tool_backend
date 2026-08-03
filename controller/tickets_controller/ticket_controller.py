from datetime import datetime, timezone
from json import JSONDecodeError
from fastapi import Request
import pymongo.errors
from starlette.responses import JSONResponse
from starlette import status
from config.config import TicketStatus, TicketErrorClassification
from utils.ticket_utility import generate_ticket_number, get_ticket_resolution_date


async def raise_ticket(request:Request):
    try:
        user_id =  request.state.user_id
        mongodb_collection = request.app.state.mongo_db

        input_data =  await request.json()

        required_input_fields = ["title","description","service","priority"]

        for field in required_input_fields:
            if field not in input_data:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content={"message":f"{field.capitalize()} is required","data":None})
            elif not input_data[field]:
                return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST,content={"detail":f"{field.capitalize()} is empty","data":None})

        title = input_data["title"]
        description = input_data["description"]
        service = input_data["service"]
        priority = input_data["priority"]
        ticket_id = await generate_ticket_number(mongodb_collection['ticket_counter'])
        ticket_status = TicketStatus.OPEN.value
        ticket_comments = None
        resolution_tat= get_ticket_resolution_date()
        error_classification = TicketErrorClassification.USER_INPUT_ERROR.value
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)

        construct_ticket_model = {
        "user_id":user_id,
        "ticket_id":ticket_id,
        "title":title,
        "description":description,
        "service":service,
        "priority":priority,
        "status":ticket_status,
        "ticket_comments":ticket_comments,
        "resolution_tat":resolution_tat,
        "error_classification":error_classification,
        "created_at":created_at,
        "updated_at":updated_at
        }

        query_response = await mongodb_collection['tickets'].insert_one(construct_ticket_model)

        return JSONResponse(status_code=status.HTTP_200_OK,content={"message":"Ticket created Successfully","data":{"ticket_id":ticket_id,"status":ticket_status,"Expected_resolution_date":resolution_tat}})

    except JSONDecodeError as e:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"message":"Invalid JSON","data":None})

    except pymongo.errors.PyMongoError as e:
        print(e)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"message":"Internal server error","data":None})


async def get_user_ticket_history(request:Request):
    try:
        user_id = request.state.user_id
        mongodb_collection = request.app.state.mongo_db

        user_tickets = await mongodb_collection['tickets'].find({"user_id":user_id},{"_id":0,"ticket_id":1,"status":1,"priority":1,"description":1,"title":1,"resolution_tat":1,"service":1,"created_at":1}).to_list(None)
        ticket_history = []
        if user_tickets:
            for ticket in user_tickets:
                formatted_ticket = {}
                for key, value in ticket.items():
                    if isinstance(value, datetime):
                        formatted_ticket[key] = value.strftime("%Y-%m-%d %H:%M:%S")
                    else:
                        formatted_ticket[key] = value

                ticket_history.append(formatted_ticket)

            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={
                    "message": "Ticket history fetched successfully",
                    "data": ticket_history,
                },
            )
        return JSONResponse(status_code=status.HTTP_200_OK,content={"message":"No Ticket history found","data":None})

    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "message": "Something went wrong",
                "error": str(e),
            },
        )






