import enum
import os
from enum import Enum

# ScoreMe API Endpoints
# We use the Sandbox URL for now. Later you can switch this easily.
SCOREME_BASE_URL = "https://sm-bsa.scoreme.in"
SCOREME_UPLOAD_URL = f"{SCOREME_BASE_URL}/bsa/external/uploadbankstatement"
SCOREME_MERGE_URL= f"{SCOREME_BASE_URL}/bsa/external/mergebankstatement"
SCOREME_BANK_NAME_URL = f"{SCOREME_BASE_URL}/bsa/external/getBankNames"

#Gst service api's
SCOREME_GST_BASE_URL= "https://sm-gst.scoreme.in"
SCOREME_GST_INFO_URL = f"{SCOREME_GST_BASE_URL}/gst/external/gstinbasicinfo"
SCORME_GST_USER_NAME_OTP = f"{SCOREME_GST_BASE_URL}/gst/external/gstgenerateotp"
SCOREME_GST_OTP_AUTHENTICATION = f"{SCOREME_GST_BASE_URL}/gst/external/gstauthentication"
SCOREME_GST_POST_GSTIN = f"{SCOREME_GST_BASE_URL}/gst/external/postgstreport"

#Itr service api's
SCORE_ME_ITR_BASE_URL = "https://sm-itr.scoreme.in"
SCOREME_FILE_ITR_LINK = f"{SCORE_ME_ITR_BASE_URL}/itr/external/fileAutomatedRequestUsingLink"
SCOREME_ITR_GET_REFERENCE_STATUS = f"{SCORE_ME_ITR_BASE_URL}/itr/external/getItrCredentialSubmissionStatus"

#Kyc service api's
SCOREME_KYC_BASE_URL = "https://sm-kyc-sync-prod.scoreme.in"
SCOREME_AADHAAR_VERIFICATION_URL=f"{SCOREME_KYC_BASE_URL}/kyc/external/aadhaarOtp"
SCOREME_AADHAAR_OTP_VERIFICATION = f"{SCOREME_KYC_BASE_URL}/kyc/external/aadhaarDetail"
SCOREME_GENERATE_DIGI_URL=f"{SCOREME_KYC_BASE_URL}/kyc/external/initiateDigiLocker"
SCOREME_DIGILOCKER_SESSION_STATUS_URL = f"{SCOREME_KYC_BASE_URL}/kyc/external/documentConsentStatus"
SCOEME_DIGILOCKER_DOCUMENT_LIST_URL = f"{SCOREME_KYC_BASE_URL}/kyc/external/documentList"
SCOREME_DICILOCKER_DOCUMENT_DOWNLOAD_URL = f"{SCOREME_KYC_BASE_URL}/kyc/external/document"


SCOREME_CIBIL_BASE_URL = "https://sm-bda.scoreme.in"
SCOREME_GENERATE_CIBIL_OTP_URL = f"{SCOREME_CIBIL_BASE_URL}/bda/external/retail"
SCOREME_VALIDATE_CIBIL_OTP_URL = f"{SCOREME_CIBIL_BASE_URL}/bda/external/validateotp"
SCOREME_RESEND_CIBIL_OTP_URL=  f"{SCOREME_CIBIL_BASE_URL}/bda/external/resendotp"



# MongoDB Settings
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "underwriting")


class KYC_FLOW_STATUS(Enum):
    CONSENT_PENDING = "CONSENT_PENDING"
    INPROGRESS = "IN_PROGRESS"
    EXPIRED = "EXPIRED"
    TIMEOUT = "TIMEOUT"
    CONSENT_APPROVED = "CONSENT_APPROVED"
    CONSENT_REJECTED = "CONSENT_REJECTED"
    ERROR = "ERROR"

class CibilOTPStatus(str, Enum):
    # OTP Generation
    OTP_SENT = "OTP_SENT"
    OTP_REJECTED = "OTP_REJECTED"

    # OTP Verification
    OTP_VERIFIED = "OTP_VERIFIED"
    OTP_INVALID = "OTP_INVALID"
    OTP_EXPIRED = "OTP_EXPIRED"

    # OTP Resend
    OTP_RESENT = "OTP_RESENT"
    OTP_RESEND_LIMIT_EXCEEDED = "OTP_RESEND_LIMIT_EXCEEDED"

    # Credit Bureau Processing
    REPORT_REQUESTED = "REPORT_REQUESTED"
    REPORT_GENERATED = "REPORT_GENERATED"
    REPORT_FAILED = "REPORT_FAILED"

    # System States
    PENDING = "PENDING"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class CibilWebhookStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"


class SiteCode(enum.Enum):
    R1X01 = "R1X01"
    PCX01 = "PCX01"



class TicketStatus(enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class TicketErrorClassification(enum.Enum):
    USER_INPUT_ERROR = "USER_INPUT_ERROR"
    BUG = "BUG"
    EXTERNAL_ERROR = "EXTERNAL_ERROR"
