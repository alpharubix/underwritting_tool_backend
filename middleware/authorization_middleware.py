import re

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import status

from utils.auth_utility import get_decoded_jwt_token


async def authorization(request: Request, call_next):
    try:
        # Bypass OPTIONS and Public Routes
        public_patterns = [
            r"^/v1/bsa/crm-bsa-statement-report/\w+$",
            r"^/v1/bsa/crm/upload$",
            r"^/v1/auth/login$",
            r"^/v1/auth/register$",
            r"^/v1/auth/forgot_password$",
            r"^/v1/auth/validate-otp$",
            r"^/v1/auth/reset_password$",
            r"^/v1/bsa/webhook-response-handler$",
            r"^/webhook/gst-statements$",
            r"^/webhook/itr-service$",
            r"^/webhook/credit-bureau",
            r"^/v1/bsa/r1xcrm-summary-of-debit-and-credit_monthwise/\d+$",
            r"^/v1/bsa/r1xcrm-cashflow/\d+$",
            r"^/v1/bsa/r1xcrm-month-wise-overview/\d+$",
            r"^/v1/bsa/r1xcrm-report-date-range/\d+$",
            r"^/v1/itr/r1xcrm-tax-calculation/\d+$",
            r"^/v1/itr/r1xcrm-balance_sheet/\d+$",
            r"^/v1/itr/r1xcrm-profit-and-loss-statement/\d+$",
            r"^/v1/itr/r1xcrm-ratio-analysis/\d+$",
            r"^/docs$",
            r"^/openapi.json$",
        ]

        # Check if the current path matches any of our regex patterns
        is_public = any(re.match(pattern, request.url.path) for pattern in public_patterns)

        if request.method == "OPTIONS" or is_public:
            return await call_next(request)

        token = request.cookies.get('access_token')
        if not token:
            return JSONResponse(
                status_code=401,
                content={"message": "Unauthorized Access"}
            )

        try:
            decoded_jwt_token = get_decoded_jwt_token(token)
            request.state.user_id = decoded_jwt_token['user_id']
            request.state.role = decoded_jwt_token['role']
        except Exception:
            return JSONResponse(status_code=401, content={'message': 'Invalid Token'})

        return await call_next(request)
    except HTTPException as e:
     raise e