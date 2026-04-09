import httpx
import os
import json

async def upload_to_scoreme(files, data_params):
    payload = {"data": json.dumps(data_params)}
    files_to_send = []
    for f in files:
        await f.seek(0)
        content = await f.read()
        files_to_send.append(("file", (f.filename, content, f.content_type)))

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://sm-bsa-sandbox.scoreme.in/bsa/external/upload",
                headers={
                    "clientId": os.getenv("CLIENT_ID"), # Matches your .env
                    "clientSecret": os.getenv("CLIENT_SECRET") # Matches your .env
                },
                data=payload,
                files=files_to_send,
                timeout=60.0
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("data")
            return None
        except Exception as e:
            print(f"ScoreMe API Exception: {e}")
            return None