from datetime import datetime, timedelta

from pymongo.asynchronous.collection import ReturnDocument




async def generate_ticket_number(mongo_db):
    counter = await mongo_db.find_one_and_update(
        {"_id": "support_ticket"},
        {"$inc": {"sequence_value": 1}},
        upsert=True,
        return_document=ReturnDocument.BEFORE
    )
    print("This is the ticket_id counter",counter)
    return counter["sequence_value"]


def get_ticket_resolution_date():
    current_date = datetime.now()

    # Monday = 0, Tuesday = 1, ..., Friday = 4, Saturday = 5, Sunday = 6
    weekday = current_date.weekday()

    if weekday == 4:  # Friday
        resolution_date = current_date + timedelta(days=3)
    elif weekday == 5:  # Saturday
        resolution_date = current_date + timedelta(days=2)
    elif weekday == 6:  # Sunday
        resolution_date = current_date + timedelta(days=1)
    else:
        resolution_date = current_date + timedelta(days=1)

    return resolution_date.strftime("%Y-%m-%d")
