import os

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
# MongoDB Settings
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "underwriting")



