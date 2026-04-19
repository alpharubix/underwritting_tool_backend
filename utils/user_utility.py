from datetime import datetime, timezone
from bson import ObjectId


def get_user_dict(account_id,email_id,phone_no,company_name,gst_number,customer_name)->dict:
            user = {
                            # Identity
                            "_id":ObjectId(),
                            "account_id":account_id,#for mapping
                            "email_id": email_id.lower(),
                            "customer_name": customer_name,
                            "email_verified": False,
                            "phone": phone_no,
                            "phone_verified": False,

                            # Company Info
                            "company_name": company_name,
                            "gst_number": gst_number,

                            # Status & Security
                            "status": "active",  # active/inactive/suspended
                            "role": "user",  # user/admin/manager
                            "is_deleted": False,

                            # Timestamps
                            "created_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc),
                            "last_login_at": None,

                            # Metadata (optional)
                            "created_by": "system",
                            "updated_by": "system",
                        }
            return  user
