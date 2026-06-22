import os
from enum import Enum

# ScoreMe API Endpoints
# We use the Sandbox URL for now. Later you can switch this easily.
SCOREME_BASE_URL = "https://sm-bsa-sandbox.scoreme.in"
SCOREME_UPLOAD_URL = f"{SCOREME_BASE_URL}/bsa/internal/uploadbankstatement"
SCOREME_REPORT_URL = f"{SCOREME_BASE_URL}/bsa/internal/getbsareport"
SCOREME_MERGE_URL= f"{SCOREME_BASE_URL}/bsa/external/mergebankstatement"

#Gst service api's
SCOREME_GST_BASE_URL= "https://sm-gst-sandbox.scoreme.in"
SCOREME_GST_INFO_URL = f"{SCOREME_GST_BASE_URL}/gst/external/gstinbasicinfo"
SCORME_GST_USER_NAME_OTP = f"{SCOREME_GST_BASE_URL}/gst/external/gstgenerateotp"
SCOREME_GST_OTP_AUTHENTICATION = f"{SCOREME_GST_BASE_URL}/gst/external/gstauthentication"
SCOREME_GST_POST_GSTIN = f"{SCOREME_GST_BASE_URL}/gst/external/postgstreport"

#Itr service api's
SCORE_ME_ITR_BASE_URL = "https://sm-itr-sandbox.scoreme.in"
SCOREME_FILE_ITR_LINK = f"{SCORE_ME_ITR_BASE_URL}/itr/external/fileAutomatedRequestUsingLink"
SCOREME_ITR_GET_REFERENCE_STATUS = f"{SCORE_ME_ITR_BASE_URL}/itr/external/getItrCredentialSubmissionStatus"

#Kyc service api's
SCOREME_KYC_BASE_URL = "https://sm-kyc-sync-sandbox.scoreme.in"
SCOREME_AADHAAR_VERIFICATION_URL=f"{SCOREME_KYC_BASE_URL}/kyc/external/aadhaarOtp"
SCOREME_AADHAAR_OTP_VERIFICATION = f"{SCOREME_KYC_BASE_URL}/kyc/external/aadhaarDetail"
SCOREME_GENERATE_DIGI_URL=f"{SCOREME_KYC_BASE_URL}/kyc/external/initiateDigiLocker"
SCOREME_DIGILOCKER_SESSION_STATUS_URL = f"{SCOREME_KYC_BASE_URL}/kyc/external/documentConsentStatus"
SCOEME_DIGILOCKER_DOCUMENT_LIST_URL = f"{SCOREME_KYC_BASE_URL}/kyc/external/documentList"
SCOREME_DICILOCKER_DOCUMENT_DOWNLOAD_URL = f"{SCOREME_KYC_BASE_URL}/kyc/external/document"

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

