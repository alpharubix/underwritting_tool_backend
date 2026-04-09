from fastapi import HTTPException, BackgroundTasks
from fastapi.routing import APIRouter
from starlette.requests import Request
from json.decoder import JSONDecodeError
auth_router = APIRouter(prefix="/v1/auth")
from controller.auth_controller import register_user, user_login, user_logout, user_reset_password


@auth_router.post("/register")
async def register(request: Request,background_tasks: BackgroundTasks):
    try:
        input_payload = await request.json()
        print(input_payload)
        mandatory_fields = (
            "customer_name",
            "company_name",
            "phone_no",
            "email_id",
            "gst_number"
        )

        missing_fields = [ #condition for checking the mandatory fields from the input
            field for field in mandatory_fields
            if field not in input_payload or not input_payload[field]
        ]

        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: {', '.join(missing_fields)}"
            )
        #if all the fields are there proceed for calling the controller
        return await register_user(input_payload,request.app.state.postgres_conn,request.app.state.mongo_db,background_tasks)

    except JSONDecodeError:# json decode error capturing for invalid data
        raise HTTPException(status_code=400, detail="Invalid body")


@auth_router.post("/login")
async def login(request: Request):
    try:
        input_payload = await request.json()
        return await user_login(request.app.state.mongo_db, input_payload)
    except JSONDecodeError:raise HTTPException(status_code=400, detail="Invalid request body")



@auth_router.post("/logout")
async def logout():
    try:
        return await user_logout()
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error please contact the administrator")

@auth_router.patch("/reset_password")
async def reset_password(request: Request):
    try:
        input_payload = await request.json()
        return await user_reset_password(request.state.user_id,request.app.state.mongo_db,input_payload)
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid request body")
