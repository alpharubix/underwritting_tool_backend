import uuid
import asyncio
from datetime import datetime, timezone
from google.cloud import storage
from dotenv import load_dotenv
load_dotenv()
import os

try:
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(os.getenv("GCS_BUCKET_NAME"))
except Exception as e:
    print("Error raised during gcp bucket connection")
    raise Exception(e)


async def upload_files_to_gcs_and_save_metadata(files, user_id, reference_id, db_connection):
    print("Files started to be uploaded")
    uploaded_files = []
    loop = asyncio.get_event_loop()

    for f in files:
        # Validate before reading
        if not f.filename.lower().endswith(".pdf"):
            raise Exception(f"{f.filename} is not a PDF")

        await f.seek(0)
        content = await f.read()

        file_id = str(uuid.uuid4())
        gcs_path = f"{user_id}/{reference_id}/{file_id}.pdf"
        blob = bucket.blob(gcs_path)

        try:
            # Non-blocking upload
            await loop.run_in_executor(
                None,
                lambda: blob.upload_from_string(content, content_type="application/pdf")
            )

            document = {
                "file_id": file_id,
                "user_id": user_id,
                "reference_id": reference_id,
                "original_file_name": f.filename,
                "gcs_path": gcs_path,
                "content_type": "application/pdf",  # Hardcoded, not from client
                "file_size": len(content),
                "uploaded_at": datetime.now(timezone.utc)
            }

            await db_connection['bsa_file_uploads'].insert_one(document)

        except Exception as e:
            await loop.run_in_executor(None, blob.delete)  # Rollback
            raise Exception(f"Upload failed for {f.filename}: {e}")

        uploaded_files.append({
            "file_id": file_id,
            "file_name": f.filename,
            "gcs_path": gcs_path
        })
        print("file uploaded successfully")

    return uploaded_files
