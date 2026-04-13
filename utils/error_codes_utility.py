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