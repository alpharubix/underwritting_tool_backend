from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import status

from utils.auth_utility import get_decoded_jwt_token


async def authorization(request: Request, call_next):
    # Bypass OPTIONS and Public Routes
    public_paths = ["/v1/auth/login", "/", "/v1/auth/register","/docs", "/openapi.json"]

    if request.method == "OPTIONS" or request.url.path in public_paths:
        return await call_next(request)

    token = request.cookies.get('access_token')
    if not token:
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={'message': 'Unauthorized Access'})

    try:
        decoded_jwt_token = get_decoded_jwt_token(token)
        request.state.user_id = decoded_jwt_token['user_id']
        request.state.role = decoded_jwt_token['role']
    except Exception:
        return JSONResponse(status_code=401, content={'message': 'Invalid Token'})

    return await call_next(request)