from fastapi.responses import JSONResponse
from fastapi.requests import Request
import starlette.status as status
from jwt import decode
async def get_analysis_date_range(
		request:Request,
		user_id:str | None =None
):
	if not user_id:
		access_token=request.cookies.get("access_token")

		if not access_token:
			return JSONResponse(content={"message":"Authorization required"},status_code=status.HTTP_401_UNAUTHORIZED)

		payload = decode(access_token)

		user_id = pa