from database.databse_config import get_mongo_db
import httpx
import asyncio


async def get_bsa_reference_documents(condition,projection):
    try:
        db = await get_mongo_db()

        ref_docs =  await db["bsa_reference"].find(condition,projection).to_list(None)

        return ref_docs

    except Exception as e:
        print(e)


async def process_webhook_document(webhook_doc,api_endpoint):
    try:
          async with httpx.AsyncClient() as client:
              response = await client.post(api_endpoint,json=webhook_doc)
              response.raise_for_status()
              return response.json()

    except Exception as e:
        print(e)


async def execute_webhook_document():
    try:
        docs = await get_bsa_reference_documents(condition={
                "is_consumed": False,
                "input_data.entityType": "Individual"},projection={})

        print("Total number of webhook documents: ",len(docs))

        for doc in docs:
            print(f"Processing webhook document for user_id:{doc['user_id']} and  reference_id:{doc['reference_id']}")

            input_body = {
  "data": {
    "jsonUrl":doc["report_urls"]["json"],
    "excelUrl":doc["report_urls"]["excel"],
    "referenceId": doc["reference_id"] ,
  },
  "responseMessage": doc["webhook_response_message"],
  "responseCode": doc["webhook_response_code"]
}
            result = await process_webhook_document(api_endpoint="http://localhost:8080/v1/bsa/webhook-response-handler",webhook_doc=input_body)
            print("End-point result",result)
            print("----------------------------------------------------------------------")
    except Exception as e:
        print(e)



asyncio.run(execute_webhook_document())


