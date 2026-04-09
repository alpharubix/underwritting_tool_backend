import uuid
from datetime import datetime, timezone
from services.extraction_service import extract_raw_data
from services.scoreme_service import upload_to_scoreme


async def handle_bsa_upload(db, files, data_params):
    # ── Validation ───────────────────────────────────────────────────────────
    extensions = {f.filename.rsplit(".", 1)[-1].lower() for f in files}
    if len(extensions) > 1:
        return {"error": "Please upload only PDF or only Excel, do not mix them."}

    batch_id   = str(uuid.uuid4())
    account_no = data_params.get("accountNumber", "UNKNOWN")

    # ── Per-file extraction & DB insert ──────────────────────────────────────
    for file in files:
        await file.seek(0)
        content = await file.read()

        raw_data = await extract_raw_data(content, file.filename)

        # raw_data == []  → table parse returned nothing (not necessarily scanned)
        # raw_data is None → explicitly detected as scanned image
        is_scanned        = raw_data is None
        extraction_status = "skipped_scan" if is_scanned else (
                            "extracted"    if raw_data else "empty")

        doc = {
            "fileName":         file.filename,
            "batchId":          batch_id,
            "accountNumber":    account_no,
            "status":           "pending",
            "referenceId":      None,
            "isScanned":        is_scanned,
            "extractionStatus": extraction_status,
            "extraction": {
                # ── The fields your reconciliation service expects ──
                "rawTransactions": raw_data or [],   # list of dicts with
                                                     # Slno/Date/Particular/
                                                     # Reference/Debit/Credit/Balance
                "extractedCount":  len(raw_data) if raw_data else 0,
                "extractedAt":     datetime.now(timezone.utc) if raw_data else None,
            },
            "scoreme": {
                "jsonUrl":    None,
                "receivedAt": None,
            },
            "createdAt": datetime.now(timezone.utc),
            "updatedAt": datetime.now(timezone.utc),
        }

        await db.bsa_uploads.insert_one(doc)
        print(f"[Controller] {file.filename} → {extraction_status} "
              f"({len(raw_data) if raw_data else 0} rows)")

    # ── Forward to ScoreMe ────────────────────────────────────────────────────
    for f in files:
        await f.seek(0)

    scoreme_data = await upload_to_scoreme(files, data_params)

    if not scoreme_data or "referenceId" not in scoreme_data:
        return {
            "batchId": batch_id,
            "status":  "partial_success",
            "message": "Local extraction saved, but ScoreMe submission failed.",
            "details": scoreme_data,
        }

    ref_id = scoreme_data["referenceId"]

    await db.bsa_uploads.update_many(
        {"batchId": batch_id},
        {"$set": {
            "referenceId": ref_id,
            "status":      "submitted",
            "updatedAt":   datetime.now(timezone.utc),
        }},
    )

    return {
        "batchId":     batch_id,
        "referenceId": ref_id,
        "message":     f"Successfully processed {len(files)} file(s).",
    }