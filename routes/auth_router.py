from fastapi import HTTPException, BackgroundTasks
from fastapi.routing import APIRouter
from starlette.requests import Request
from json.decoder import JSONDecodeError
from utils.auth_utility import is_password_valid
auth_router = APIRouter(prefix="/v1/auth")
from controller.auth_controller import register_user, user_login, user_logout, user_reset_password,forget_password,validate_forgot_password_otp,reset_password_


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
            "password"
        )

        missing_fields = [ #condition for checking the mandatory fields from the input
            field for field in mandatory_fields
            if field not in input_payload or not input_payload[field]
        ]

        if missing_fields:
            raise HTTPException(
                status_code=400,
                detail={"message":f"Missing required fields: {', '.join(missing_fields)}"}
            )
        #validate the password before passing the input to the cpntroller
        result,detail = is_password_valid(input_payload["password"])

        if not result:
            raise HTTPException(status_code=400, detail={"message": f"{detail}"})

        #if all the fields are there proceed for calling the controller
        return await register_user(input_payload,request.app.state.postgres_conn,request.app.state.mongo_db,background_tasks)

    except JSONDecodeError:# json decode error capturing for invalid data
        raise HTTPException(status_code=400, detail={"message":"Invalid body"})


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

@auth_router.patch("/update_password")
async def reset_password(request: Request):
    try:
        input_payload = await request.json()
        return await user_reset_password(request.state.user_id,request.app.state.mongo_db,input_payload)
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid request body")

@auth_router.post("/forgot_password")
async def forgot_password(request: Request,background_tasks: BackgroundTasks):
    try:
        input_payload = await request.json()
        email_id = input_payload.get("email_id",None)
        return await forget_password(email_id,request.app.state.mongo_db,background_tasks)
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid request body")
    except HTTPException as e:
        raise e

@auth_router.post("/validate-otp")
async def validate_otp (request: Request):
    try:
        input_payload = await request.json()
        email_id = input_payload.get("email_id",None)
        otp = input_payload.get("otp",None)
        return await validate_forgot_password_otp(email_id,otp,request.app.state.mongo_db)
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid request body")
    except HTTPException as e:
        raise e
@auth_router.post("/reset_password")
async def reset_password(request: Request):
    try:
        input_payload = await request.json()
        reset_token = input_payload.get("reset_token",None)
        new_password = input_payload.get("new_password",None)
        return await reset_password_(reset_token,new_password,request.app.state.mongo_db)
    except JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid request body")
    except HTTPException as e:
        raise e
