
def create_body_for_new_registration(data: dict) -> str:
    try:
        name = data.get("name", "User")
        login_id = data.get("login_id", "")
        password = data.get("password", "")
        login_url = data.get("login_url", "https://yourapp.com/login")

        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                    <td align="center">
                        <table width="600px" style="background-color: #ffffff; padding: 20px; border-radius: 8px;">

                            <tr>
                                <td>
                                    <h2 style="color: #333;">Welcome to 5PointCredit 🎉</h2>
                                </td>
                            </tr>

                            <tr>
                                <td>
                                    <p style="font-size: 16px; color: #555;">
                                        Hi {name},
                                    </p>
                                    <p style="font-size: 16px; color: #555;">
                                        Your account has been successfully created. You can now log in using the credentials below:
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="background-color: #f9f9f9; padding: 15px; border-radius: 5px;">
                                    <p><strong>Login ID:</strong> {login_id}</p>
                                    <p><strong>Password:</strong> {password}</p>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding-top: 20px;">
                                    <a href="{login_url}" 
                                       style="display: inline-block; padding: 12px 20px; background-color: #007BFF; color: #ffffff; text-decoration: none; border-radius: 5px;">
                                        Login to Your Account
                                    </a>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding-top: 20px;">
                                    <p style="font-size: 14px; color: #888;">
                                        For security reasons, we recommend changing your password after your first login.
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding-top: 10px;">
                                    <p style="font-size: 14px; color: #888;">
                                        If you did not request this account, please ignore this email.
                                    </p>
                                </td>
                            </tr>

                            <tr>
                                <td style="padding-top: 20px;">
                                    <p style="font-size: 14px; color: #555;">
                                        Regards,<br>
                                        5PointCredit Team
                                    </p>
                                </td>
                            </tr>

                        </table>
                    </td>
                </tr>
            </table>
        </body>
        </html>
        """

        return html_body

    except Exception as e:
        print("Error creating email body:", e)
        return ""