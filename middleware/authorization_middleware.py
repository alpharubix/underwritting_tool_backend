import re

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import status

from utils.auth_utility import get_decoded_jwt_token


async def authorization(request: Request, call_next):
    # Bypass OPTIONS and Public Routes
    public_patterns = [
        r"^/v1/bsa/crm-bsa-statement-report/\w+$",
        r"^/v1/bsa/crm/upload$",
        r"^/v1/auth/login$",
        r"^/v1/auth/register$",
        r"^/v1/auth/forgot_password$",
        r"^/v1/auth/validate-otp$",
        r"^/v1/auth/reset_password$"
        r"^/docs$",
        r"^/openapi.json$",
    ]

    # Check if the current path matches any of our regex patterns
    is_public = any(re.match(pattern, request.url.path) for pattern in public_patterns)

    if request.method == "OPTIONS" or is_public:
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