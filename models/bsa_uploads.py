from datetime import datetime, timezone

def create_bsa_upload(file_name: str, is_scanned: bool, batch_id: str, account_number: str):
    return {
        "fileName": file_name,
        "batchId": batch_id,
        "accountNumber": account_number,
        "status": "pending",
        "referenceId": None,
        "isScanned": is_scanned,
        "extraction": {
            "rawTransactions": [], # We will fill this in the controller
            "extractedAt": None 
        },
        "scoreme": {
            "jsonUrl": None,
            "receivedAt": None
        },
        "createdAt": datetime.now(timezone.utc),
        "updatedAt": datetime.now(timezone.utc)
    }