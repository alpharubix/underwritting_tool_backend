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

    "EGI404": (
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