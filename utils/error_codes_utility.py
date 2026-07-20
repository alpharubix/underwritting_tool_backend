from starlette import status



SCOREME_BSA__ERROR_MAP = {
    "EBF017": (status.HTTP_400_BAD_REQUEST,  "Blank Input Field."),
    "EIP018": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Incorrect Input."),
    "EPI022": (status.HTTP_400_BAD_REQUEST,  "Payload is Incorrect."),
    "EFE030": (status.HTTP_400_BAD_REQUEST,  "File is Empty."),
    "EFS106": (status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File size exceeds the allowed limit."),
    "EIB065": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Incorrect Bank Code."),
    "EAT064": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Incorrect Account Type."),
    "EIE066": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Incorrect Entity Type."),
    "EAN093": (status.HTTP_422_UNPROCESSABLE_ENTITY, "Incorrect Account Number."),
    "ENF031": (status.HTTP_400_BAD_REQUEST,  "Number of Files are more than allowed limit."),
    "EFT032": (status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Incorrect File Type."),
    "ERE1203":(status.HTTP_429_TOO_MANY_REQUESTS, "Number of requests exceeds the allowed limit for a loan application."),
    "EDP1209":(status.HTTP_409_CONFLICT, "The input provided for the entered application id is duplicate. Please use a new application Id."),
    "EIF009": (status.HTTP_400_BAD_REQUEST,  "Incorrect File."),
    "EFP070": (status.HTTP_400_BAD_REQUEST,  "File Password not Found."),
    "EIP069": (status.HTTP_401_UNAUTHORIZED, "Incorrect File Password."),
    "EUA012": (status.HTTP_401_UNAUTHORIZED, "Unauthorized Access."),
}


SCOREME_GST_BASIC_INFO_ERROR_MAP = {
    "EBF017": (
        status.HTTP_400_BAD_REQUEST,
        "Blank Input Field."
    ),

    "EIP018": (
        status.HTTP_400_BAD_REQUEST,
        "Incorrect Input."
    ),

    "EPI022": (
        status.HTTP_400_BAD_REQUEST,
        "Payload is Incorrect."
    ),

    "ERE1203": (
        status.HTTP_429_TOO_MANY_REQUESTS,
        "Number of requests exceeds the allowed limit for a loan application."
    ),

    "EDP1209": (
        status.HTTP_409_CONFLICT,
        "The input provided for the entered application id is duplicate. Please use a new application Id."
    ),

    "EUP007": (
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "Unable To Process. Please Reach Out To Support."
    ),

    "EGN014": (
        status.HTTP_404_NOT_FOUND,
        "GSTIN Not found Or Incorrect GSTIN."
    ),
}

SCOREME_GST_OTP_ERROR_MAP = {
    "EBF017": {
        "status_code": 400,
        "message": "Blank Input Field."
    },
    "EIP018": {
        "status_code": 400,
        "message": "Incorrect Input."
    },
    "EPI022": {
        "status_code": 400,
        "message": "Payload is Incorrect."
    },
    "EGU036": {
        "status_code": 400,
        "message": "Number of GSTIN and username entered do not match."
    },
    "ENG034": {
        "status_code": 400,
        "message": "GSTINs entered cannot be same."
    },
    "EAS517": {
        "status_code": 429,
        "message": "OTP already sent. Please try again later."
    },
    "ERO038": {
        "status_code": 500,
        "message": "GST OTP generation unsuccessful."
    },
    "EAA049": {
        "status_code": 401,
        "message": "API Access/GSTIN Username Error."
    },
    "EIS050": {
        "status_code": 503,
        "message": "Information Source is Not Working."
    }
}

SCOREME_GST_OTP_VALIDATE_ERROR_MAP = {
    "EBF017": (400, "Blank Input Field."),
    "EIP018": (400, "Incorrect Input."),
    "EPI022": (400, "Payload is Incorrect."),
    "EGO040": (400, "Number of GSTIN and OTP entered do not match."),
    "ENG034": (400, "GSTINs entered cannot be same."),
    "EGO039": (400, "Please generate OTP first."),
    "EGU051": (400, "GSTIN and Username does not match."),
    "EGO045": (400, "GSTIN OTP Expired. Please regenerate OTP."),
    "EAU043": (401, "GSTIN Authentication Unsuccessful."),
    "EIS042": (503, "Information Source is Not Working."),
}

SCOREME_GST_POST_GSTIN_ERROR_MAP = {
    "EBF017": {
        "status_code": 400,
        "message": "Blank Input Field."
    },
    "EIP018": {
        "status_code": 400,
        "message": "Incorrect Input."
    },
    "EPI022": {
        "status_code": 400,
        "message": "Payload is Incorrect."
    },
    "EVP085": {
        "status_code": 400,
        "message": "Mismatch in value of parameters companyName and reportType."
    },
    "ENG034": {
        "status_code": 400,
        "message": "GSTINs entered cannot be same."
    },
    "EPG044": {
        "status_code": 400,
        "message": "PAN is not same for the GSTINs entered."
    },
    "ERT146": {
        "status_code": 400,
        "message": "The requested months are more than the allowed limit."
    },
    "ERE1203": {
        "status_code": 429,
        "message": "Number of requests exceeds the allowed limit for a loan application."
    },
    "EDP1209": {
        "status_code": 409,
        "message": "The input provided for the entered application id is duplicate. Please use a new application Id."
    },
    "EIS042": {
        "status_code": 503,
        "message": "Information Source is Not Working."
    },
    "EOA048": {
        "status_code": 401,
        "message": "Please complete the GST OTP generation and authentication process."
    },
    "EAE052": {
        "status_code": 401,
        "message": "Authentication expired. Please generate OTP and authenticate again."
    }
}

SCOREME_ITR_POST_LINK_ERROR_MAP = {
    "EPI022": {
        "message": "Payload is Incorrect.",
        "status_code": 400,
        "data": None
    },
    "EBF017": {
        "message": "Blank Input Field.",
        "status_code": 400,
        "data": None
    },
    "EIP018": {
        "message": "Incorrect Input.",
        "status_code":400,
        "data": None
    },
    "ETI019": {
        "message": "Technical Issue. Please Try Again.",
        "status_code":500,
        "data": None
    }
}

SCOREME_AADHAAR_OTP_ERROR_MAP = {
    "EBF017": {
        "message": "Blank Input Field.",
        "status_code": 400,
        "data": None
    },
    "EIP018": {
        "message": "Incorrect Input.",
        "status_code": 400,
        "data": None
    },
    "EPI022": {
        "message": "Payload is Incorrect.",
        "status_code": 400,
        "data": None
    },
    "EIS042": {
        "message": "Information Source is Not Working.",
        "status_code": 503,
        "data": None
    },
    "EUP007": {
        "message": "Unable To Process. Please Reach Out To Support.",
        "status_code": 500,
        "data": None
    },
    "EAN1229": {
        "message": "Aadhaar number does not have a mobile number registered with it.",
        "status_code": 400,
        "data": None
    },
    "EAN1391": {
        "message": "Aadhaar locked by the Aadhaar number holder.",
        "status_code": 403,
        "data": None
    },
    "EAE168": {
        "message": "Aadhaar does not exist.",
        "status_code": 404,
        "data": None
    },
    "ERT788": {
        "message": "Request Timed Out.",
        "status_code": 504,
        "data": None
    },
    "EAS517": {
        "message": "OTP already sent. Please try after 120 Sec.",
        "status_code": 429,
        "data": None
    },
    "EML1916": {
        "message": "You've reached the maximum number of attempts.",
        "status_code": 429,
        "data": None
    }
}
AADHAAR_OTP_ERROR_MAP = {
    "EBF017": {
        "status_code": 400,
        "message": "Blank Input Field.",
        "data": {}
    },
    "EIP018": {
        "status_code": 400,
        "message": "Incorrect Input.",
        "data": {}
    },
    "EPI022": {
        "status_code": 400,
        "message": "Payload is Incorrect.",
        "data": {}
    },
    "EIS042": {
        "status_code": 503,
        "message": "Information Source is Not Working.",
        "data": {}
    },
    "EUP007": {
        "status_code": 500,
        "message": "Unable To Process. Please Reach Out To Support.",
        "data": {}
    },
    "ETP011": {
        "status_code": 400,
        "message": "Incorrect OTP.",
        "data": {}
    },
    "EOE794": {
        "status_code": 400,
        "message": "OTP either expired or not generated yet. Kindly regenerate OTP.",
        "data": {}
    },
    "EAS517": {
        "status_code": 429,
        "message": "OTP already sent. Please try after 10 min.",
        "data": {}
    },
    "EOE082": {
        "status_code": 400,
        "message": "OTP Expired.",
        "data": {}
    },
    "ELE077": {
        "status_code": 400,
        "message": "OTP Link Expired.",
        "data": {}
    },
    "EAN1390": {
        "status_code": 400,
        "message": "Your Aadhaar has been suspended or cancelled.",
        "data": {}
    },
    "ERT788": {
        "status_code": 408,
        "message": "Request Timed Out.",
        "data": {}
    }
}

DIGIOCKER_URL_ERROR_MAP = {
    "EBF017": {
        "status_code": 400,
        "message": "Blank Input Field.",
        "data": {}
    },
    "EPI022": {
        "status_code": 400,
        "message": "Payload is Incorrect.",
        "data": {}
    },
    "EIP018": {
        "status_code": 400,
        "message": "Incorrect Input.",
        "data": {}
    },
    "EIS042": {
        "status_code": 503,
        "message": "Information Source is Not Working.",
        "data": {}
    },
    "EUP007": {
        "status_code": 500,
        "message": "Unable To Process. Please Reach Out To Support.",
        "data": {}
    },
    "ERT788": {
        "status_code": 504,
        "message": "Request Timed Out.",
        "data": {}
    }
}

DIGILOCKER_SESSION_STATUS_ERROR_MAP = {
    "SRC001": {
        "message": "Successfully Completed.",
        "data": {},
        "responseCode": "SRC001"
    },
    "RNP020": {
        "message": "Request may be in process. Please wait for some time.",
        "data": {},
        "responseCode": "RNP020"
    },
    "EBF017": {
        "message": "Blank Input Field.",
        "data": {},
        "responseCode": "EBF017"
    },
    "EPI022": {
        "message": "Payload is Incorrect.",
        "data": {},
        "responseCode": "EPI022"
    },
    "EIP018": {
        "message": "Incorrect Input.",
        "data": {},
        "responseCode": "EIP018"
    },
    "EAF1654": {
        "message": "Aadhaar is mandatory from Digi locker. The Aadhaar checkbox must remain selected while proceeding.",
        "data": {},
        "responseCode": "EAF1654"
    },
    "EIS042": {
        "message": "Information Source is Not Working.",
        "data": {},
        "responseCode": "EIS042"
    },
    "EUP007": {
        "message": "Unable To Process. Please Reach Out To Support.",
        "data": {},
        "responseCode": "EUP007"
    },
    "ERT788": {
        "message": "Request Timed Out.",
        "data": {},
        "responseCode": "ERT788"
    },
    "ENI004": {
        "message": "No Information Found.",
        "data": {},
        "responseCode": "ENI004"
    }
}

DIGILOCKER_DOCUMENT_LIST_ERROR_MAP = {
    "EBF017": {
        "message": "Blank Input Field.",
        "data": {}
    },
    "EPI022": {
        "message": "Payload is Incorrect.",
        "data": {}
    },
    "EIP018": {
        "message": "Incorrect Input.",
        "data": {}
    },
    "EIS042": {
        "message": "Information Source is Not Working.",
        "data": {}
    },
    "EUP007": {
        "message": "Unable To Process. Please Reach Out To Support.",
        "data": {}
    },
    "ERT788": {
        "message": "Request Timed Out.",
        "data": {}
    },
    "ENI004": {
        "message": "No Information Found.",
        "data": {}
    }
}

DIGILOCKER_GET_DOCUMENT_ERROR_MAP = {
    "EBF017": {
        "message": "Blank Input Field.",
        "status_code": 400,
        "data": {}
    },
    "EPI022": {
        "message": "Payload is Incorrect.",
        "status_code": 400,
        "data": {}
    },
    "EIP018": {
        "message": "Incorrect Input.",
        "status_code": 400,
        "data": {}
    },
    "EIS042": {
        "message": "Information Source is Not Working.",
        "status_code": 503,
        "data": {}
    },
    "EUP007": {
        "message": "Unable To Process. Please Reach Out To Support.",
        "status_code": 500,
        "data": {}
    },
    "ERT788": {
        "message": "Request Timed Out.",
        "status_code": 408,
        "data": {}
    },
    "ENI004": {
        "message": "No Information Found.",
        "status_code": 404,
        "data": {}
    },
    "EUA1655":{
        "status_code": 400,
        "message":"User access denied",
        "data":{}

    }
}

CIBIL_BUREAU_GENERATE_OTP_ERROR_MAP = {
    "EPI022": {
        "message": "Payload is Incorrect.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "EEI2002": {
        "message": "Error in Input.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "ELN2004": {
        "message": "Error in First Name.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "ELN2005": {
        "message": "Error in Last Name.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "EEA2006": {
        "message": "Error in Address.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "EBF017": {
        "message": "Blank Input Field.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "EIB721": {
        "message": "Incorrect Bureau Type.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "ENR901": {
        "message": "Number of requests exceeds the allowed limit.",
        "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
    },
    "EEG2015": {
        "message": "Error in Gender.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "EIN2009": {
        "message": "Error in Identity Number.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "EMN2010": {
        "message": "Error in Mobile Number.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "EDB2012": {
        "message": "Error in Date of Birth format.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "ESC2008": {
        "message": "Error in State Code.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "EEP2007": {
        "message": "Error in Pincode.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "EMS2013": {
        "message": "Mismatch between State Code and Pincode.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "EMN2014": {
        "message": "Error in Middle Name.",
        "status_code": status.HTTP_400_BAD_REQUEST,
    },
    "ELL420": {
        "message": "Login attempts limit exceeded.",
        "status_code": status.HTTP_429_TOO_MANY_REQUESTS,
    },
}

CIBIL_VALIDATE_OTP_ERROR_MAP = {
    "ETP011": {"message": "Incorrect OTP", "status_code": status.HTTP_400_BAD_REQUEST},
    "SOS176": {"message": "OTP expired", "status_code": status.HTTP_400_BAD_REQUEST},
    "SOS177": {"message": "Maximum OTP attempts exceeded", "status_code": status.HTTP_429_TOO_MANY_REQUESTS},
    "SOS178": {"message": "OTP not found", "status_code": status.HTTP_404_NOT_FOUND},
    "ERR541":{"message":"OTP either expired or not generated yet. Please reinitiate request again", "status_code": status.HTTP_400_BAD_REQUEST},
    "ECB846": {"message":"Consumer not found in bureau","status_code": status.HTTP_400_BAD_REQUEST},
    "EPN492":{"message":"Phone number does not match with Bureau","status_code": status.HTTP_400_BAD_REQUEST}

}

CIBIL_RESEND_OTP_ERROR_CODES = {
    "SOS174": {
        "status_code": 200,
        "message": "OTP successfully sent to mobile number."
    },
    "ERU061": {
        "status_code": 400,
        "message": "OTP has already been verified."
    },
    "ECI419": {
        "status_code": 500,
        "message": "Credit Bureau service configuration error. Please try again later."
    },
    "EGD509": {
        "status_code": 502,
        "message": "Credit Bureau service is currently unavailable. Please try again later."
    },
    "ERR541":{
        "status_code": 400,
        "message":"OTP either expired or not generated yet. Please reinitiate request again"
    }
}