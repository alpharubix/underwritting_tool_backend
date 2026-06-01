from bson import ObjectId
from controller.email_controller import send_mail
from utils.email_utility import create_body_for_new_registration, build_bsa_report_mail_body, \
    create_body_for_password_reset, build_gst_email_body, build_itr_report_mail_body


def send_registration_mail_to_user(to,data):
    formated_body = create_body_for_new_registration(data)
    subject = "Welcome to 5PointCredit! Get Started Now"
    return send_mail(to, subject,formated_body)


async def send_report_mail_based_on_request(user_id, reference_id, mongodb, pg_db):
    try:
        doc = await mongodb['bsa_reference'].find_one({'reference_id':reference_id})

        if not doc:
            print(f"[Mail] No BSA reference document found for reference_id: {reference_id}")
            return

        is_crm = doc.get("is_request_from_crm", False)

        # ── Resolve recipient
        if is_crm:
            crm_user_info  = doc.get("crm_user_info") or {}
            to_email       = crm_user_info.get("email")
            recipient_name = crm_user_info.get("full_name", )
        else:
            user_row = await mongodb['users'].find_one({'_id': ObjectId(user_id)})
            if not user_row:
                print(f"[Mail] User not found in 5point credit system for user_id: {user_id}")
                return
            user           = dict(user_row)
            to_email       = user.get("email_id")
            recipient_name = user.get("company_name", "User")

        if not to_email:
            print(f"[Mail] No email resolved for user_id: {user_id}")
            return

        subject, body = build_bsa_report_mail_body(
            recipient_name = recipient_name,
            reference_id   = reference_id,
            is_crm         = is_crm
        )

        send_mail(to=to_email, subject=subject, body=body)

    except Exception as e:
        print(f"[Mail] Failed to send BSA report mail for reference_id {reference_id}: {e}")


def send_reset_email_to_user(to, otp):
    formatted_body = create_body_for_password_reset(otp)
    subject = "5PointCredit Password Reset Code 🔐"
    return send_mail(to, subject, formatted_body)

async def send_gst_report_mail_based_on_request(user_id, reference_id, mongodb):
    try:
        user_row = await mongodb['users'].find_one(
            {'_id': ObjectId(user_id)},
            {
                "email_id": 1,
                "company_name": 1
            }
        )

        if not user_row:
            print(f"[Mail] User not found for user_id: {user_id}")
            return

        to_email = user_row.get("email_id")
        recipient_name = user_row.get("company_name", "User")

        if not to_email:
            print(f"[Mail] No email found for user_id: {user_id}")
            return

        body = build_gst_email_body(
            user_name= recipient_name,
            reference_id=reference_id
        )

        send_mail(
            to=to_email,
            subject="Your GST Report Is Ready for Review",
            body=body
        )

        print(
            f"[Mail] GST report mail sent successfully "
            f"for reference_id: {reference_id}"
        )

    except Exception as e:
        print(
            f"[Mail] Failed to send GST report mail "
            f"for reference_id {reference_id}: {e}"
        )


async def send_itr_report_mail_based_on_request(
    user_id: str,
    reference_id: str,
    mongodb
):
    try:
        user_row = await mongodb['users'].find_one(
            {'_id': ObjectId(user_id)},
            {
                "email_id": 1,
                "company_name": 1
            }
        )

        if not user_row:
            print(f"[Mail] User not found for user_id: {user_id}")
            return

        to_email = user_row.get("email_id")
        recipient_name = user_row.get("company_name", "User")

        if not to_email:
            print(f"[Mail] No email found for user_id: {user_id}")
            return

        subject, body = build_itr_report_mail_body(
            recipient_name=recipient_name,
            reference_id=reference_id
        )

        send_mail(
            to=to_email,
            subject=subject,
            body=body
        )

        print(
            f"[Mail] ITR report mail sent successfully "
            f"for reference_id: {reference_id}"
        )

    except Exception as e:
        print(
            f"[Mail] Failed to send ITR report mail "
            f"for reference_id {reference_id}: {e}"
        )