import os

# ScoreMe API Endpoints
# We use the Sandbox URL for now. Later you can switch this easily.
SCOREME_BASE_URL = "https://sm-bsa-sandbox.scoreme.in"
SCOREME_UPLOAD_URL = f"{SCOREME_BASE_URL}/bsa/internal/uploadbankstatement"
SCOREME_REPORT_URL = f"{SCOREME_BASE_URL}/bsa/internal/getbsareport"
SCOREME_MERGE_URL= f"{SCOREME_BASE_URL}/bsa/external/mergebankstatement"

# MongoDB Settings
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "underwriting")