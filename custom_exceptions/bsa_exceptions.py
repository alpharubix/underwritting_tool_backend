from fastapi import HTTPException

from utils.error_codes_utility import SCOREME_BSA__ERROR_MAP

def raise_bsa_exception(result:dict):
    """Raises an HTTPException based on ScoreMe's responseCode, if it's an error."""
    response_code = result.get("responseCode")
    if response_code and response_code in SCOREME_BSA__ERROR_MAP:
        http_status, message = SCOREME_BSA__ERROR_MAP[response_code]
        print("http exception is raised accordingly")
        raise HTTPException(
            status_code=http_status,
            detail={
                "Message": message,
            }
        )