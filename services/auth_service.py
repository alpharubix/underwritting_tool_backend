import asyncpg.connection
from starlette import status
from starlette.exceptions import HTTPException


async def get_crm_user(crm_user_id: int, pg_db: asyncpg.Connection):
    try:
        if not crm_user_id or str(crm_user_id).strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "crm_user_id is required"}
            )

        query = """
            SELECT id,full_name,email FROM users WHERE id = $1
        """

        user = await pg_db.fetchrow(query, crm_user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "message": (
                        "Access Denied Please contact the administrator"
                    )
                }
            )

        return dict(user)  # asyncpg returns a Record object, cast to dict for uniform access

    except HTTPException as e:
        raise e
    except asyncpg.PostgresError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Database error while fetching CRM user: {str(e)}"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Unexpected error: {str(e)}"}
        )