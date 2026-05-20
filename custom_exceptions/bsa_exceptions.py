from fastapi import HTTPException
from utils.error_codes_utility import SCOREME_BSA__ERROR_MAP,SCOREME_GST_BASIC_INFO_ERROR_MAP,SCOREME_GST_OTP_ERROR_MAP,SCOREME_GST_OTP_VALIDATE_ERROR_MAP,SCOREME_GST_POST_GSTIN_ERROR_MAP

def raise_bsa_exception(result:dict):
    """Raises an HTTPException based on ScoreMe's responseCode, if it's an error."""
    response_code = result.get("responseCode")
    if response_code and response_code in SCOREME_BSA__ERROR_MAP:
        http_status, message = SCOREME_BSA__ERROR_MAP[response_code]
        print("http exception is raised accordingly")
        raise HTTPException(
            status_code=http_status,
            detail={
                "message": message,
                "responseCode": response_code
            }
        )

def raise_gst_basic_info_expectation(result:dict):
    """Raises an HTTPException based on ScoreMe's responseCode, if it's an error."""
    response_code = result.get("responseCode")
    if response_code and response_code in SCOREME_GST_BASIC_INFO_ERROR_MAP:
        http_status, message = SCOREME_GST_BASIC_INFO_ERROR_MAP[response_code]
        print("http exception is raised accordingly")
        raise HTTPException(
            status_code=http_status,
            detail={
                "message": message,
                "responseCode": response_code
            }
        )

def raise_gst_otp_expectation(result:dict):
    response_code = result.get("responseCode")
    if response_code and response_code in SCOREME_GST_OTP_ERROR_MAP:
        http_status, message = SCOREME_GST_OTP_ERROR_MAP[response_code]
        print("http exception is raised accordingly")
        raise HTTPException(
            status_code=http_status,
            detail={
                "message": message,
                "responseCode": response_code
            }
        )

def raise_gst_validate_otp_exception(result: dict):
    response_code = result.get("responseCode")
    if response_code and response_code in SCOREME_GST_OTP_VALIDATE_ERROR_MAP:
        http_status, message = SCOREME_GST_OTP_VALIDATE_ERROR_MAP[response_code]
        raise HTTPException(
            status_code=http_status,
            detail={"message": message,"responseCode": response_code}
        )


def raise_gst_post_gstin_exception(result: dict):
    response_code = result.get("responseCode")
    if response_code and response_code in SCOREME_GST_POST_GSTIN_ERROR_MAP :
        http_status, message = SCOREME_GST_POST_GSTIN_ERROR_MAP[response_code]
        raise HTTPException(
            status_code=http_status,
            detail={"message": message,"responseCode": response_code}
        )