from starlette import status
from fastapi import HTTPException
from starlette.responses import JSONResponse
from utils.error_codes_utility import SCOREME_BSA__ERROR_MAP, SCOREME_GST_BASIC_INFO_ERROR_MAP, \
    SCOREME_GST_OTP_ERROR_MAP, SCOREME_GST_OTP_VALIDATE_ERROR_MAP, SCOREME_GST_POST_GSTIN_ERROR_MAP, \
    SCOREME_ITR_POST_LINK_ERROR_MAP, SCOREME_AADHAAR_OTP_ERROR_MAP, AADHAAR_OTP_ERROR_MAP, DIGIOCKER_URL_ERROR_MAP, \
    DIGILOCKER_DOCUMENT_LIST_ERROR_MAP, DIGILOCKER_GET_DOCUMENT_ERROR_MAP, CIBIL_BUREAU_GENERATE_OTP_ERROR_MAP, \
    CIBIL_VALIDATE_OTP_ERROR_MAP, CIBIL_RESEND_OTP_ERROR_CODES


def raise_bsa_exception(result:dict):
    """Raises an HTTPException based on ScoreMe's responseCode, if it's an error."""
    response_code = result.get("responseCode")
    if response_code in SCOREME_BSA__ERROR_MAP:
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
        error_dict = SCOREME_GST_OTP_ERROR_MAP[response_code]
        print("http exception is raised accordingly")
        raise HTTPException(
            status_code=error_dict["status_code"],
            detail={"message": error_dict["message"], "responseCode": response_code}
        )

def raise_gst_validate_otp_exception(result: dict):
    response_code = result.get("responseCode")
    if response_code and response_code in SCOREME_GST_OTP_VALIDATE_ERROR_MAP:
        error_dict = SCOREME_GST_OTP_VALIDATE_ERROR_MAP[response_code]
        raise HTTPException(
            status_code=error_dict["status_code"],
            detail={"message": error_dict["message"], "responseCode": response_code}
        )


def raise_gst_post_gstin_exception(result: dict):
    response_code = result.get("responseCode")
    if response_code in SCOREME_GST_POST_GSTIN_ERROR_MAP :
        error_dict =  SCOREME_GST_POST_GSTIN_ERROR_MAP[response_code]
        raise HTTPException(
            status_code=error_dict["status_code"],
            detail={"message": error_dict["message"],"responseCode": response_code}
        )

def raise_itr_post_link_exception(result: dict):
    response_code = result.get("responseCode")
    if response_code in SCOREME_ITR_POST_LINK_ERROR_MAP :
        error_dict =  SCOREME_ITR_POST_LINK_ERROR_MAP[response_code]
        raise HTTPException(
            status_code=error_dict["status_code"],
            detail={"message": error_dict["message"],"responseCode": response_code,"data":error_dict["data"]}
        )

def raise_aadhaar_verification_exception(result: dict):
    response_code = result.get("responseCode")

    if response_code in SCOREME_AADHAAR_OTP_ERROR_MAP:
        error_dict = SCOREME_AADHAAR_OTP_ERROR_MAP[response_code]

        raise HTTPException(
            status_code=error_dict["status_code"],
            detail={
                "message": error_dict["message"],
                "responseCode": response_code,
                "data": error_dict["data"]
            }
        )

def raise_digilocker_url_exception(result: dict):
    response_code = result.get("responseCode")

    if response_code in DIGIOCKER_URL_ERROR_MAP:
        error_dict = DIGIOCKER_URL_ERROR_MAP[response_code]

        raise HTTPException(
            status_code=error_dict["status_code"],
            detail={
                "message": error_dict["message"],
                "responseCode": response_code,
                "data": error_dict["data"]
            }
        )

def raise_aadhaar_otp_exception(result: dict):
    response_code = result.get("responseCode")

    if response_code in AADHAAR_OTP_ERROR_MAP:
        error_dict = AADHAAR_OTP_ERROR_MAP[response_code]

        raise HTTPException(
            status_code=error_dict["status_code"],
            detail={
                "message": error_dict["message"],
                "responseCode": response_code,
                "data": error_dict["data"]
            }
        )

def raise_digilocker_document_list_exception(result: dict):
    response_code = result.get("responseCode")

    if response_code in DIGILOCKER_DOCUMENT_LIST_ERROR_MAP:
        error_dict = DIGILOCKER_DOCUMENT_LIST_ERROR_MAP[response_code]

        raise HTTPException(
            status_code=error_dict["status_code"],
            detail={
                "message": error_dict["message"],
                "responseCode": response_code,
                "data": error_dict["data"]
            }
        )

def raise_digilocker_document_url(result: dict):
    response_code = result.get("responseCode")

    if response_code in DIGILOCKER_GET_DOCUMENT_ERROR_MAP:
        error_dict = DIGILOCKER_GET_DOCUMENT_ERROR_MAP[response_code]

        raise HTTPException(
            status_code=error_dict["status_code"],
            detail={
                "message": error_dict["message"],
                "responseCode": response_code,
                "data": error_dict["data"]
            }
        )

def raise_cibil_otp_exception(result: dict):
    response_code = result.get("responseCode")

    if response_code in CIBIL_BUREAU_GENERATE_OTP_ERROR_MAP:
        error_dict = CIBIL_BUREAU_GENERATE_OTP_ERROR_MAP[response_code]
        return JSONResponse(status_code=error_dict['status_code'],content={"message":error_dict['message'],"data":None,"responsecode":response_code})
    else:
        return  JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,content={"message":"Unknown error contact admin for support","data":None,"responsecode":"SYS_INT_ERR"})

def raise_cibil_validate_otp_exception(result: dict):
     response_code = result.get("responseCode")

     if response_code in CIBIL_VALIDATE_OTP_ERROR_MAP:
         error_dict = CIBIL_VALIDATE_OTP_ERROR_MAP[response_code]
         return JSONResponse(status_code=error_dict['status_code'],
                             content={"message": error_dict['message'], "data": None, "responsecode": response_code})
     else:
         return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                             content={"message": "Unknown error contact admin for support", "data": None,
                                      "responsecode": "SYS_INT_ERR"})

def raise_cibil_resend_otp_exception(result: dict):
    response_code = result.get("responseCode")

    if response_code in CIBIL_RESEND_OTP_ERROR_CODES :
        error_dict =CIBIL_RESEND_OTP_ERROR_CODES[response_code]
        return JSONResponse(status_code=error_dict['status_code'],
                            content={"message": error_dict['message'], "data": None, "responsecode": response_code})
    else:
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            content={"message": "Unknown error contact admin for support", "data": None,
                                     "responsecode": "SYS_INT_ERR"})