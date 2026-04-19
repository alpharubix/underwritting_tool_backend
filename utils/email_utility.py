
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

def build_bsa_report_mail_body(
    recipient_name: str,
    reference_id: str,
    is_crm: bool
) -> tuple[str, str]:

    if is_crm:
        app_label = "Open CRM Application"
        app_url   = "https://r1xchange-crm.netlify.app/login"       # replace with actual CRM URL
        app_note  = "Log in to your CRM portal to view the full analysis."
        btn_color = "#1E3A5F"
    else:
        app_label = "Open 5PointCredit"
        app_url   = "https://5pointcredit.com/"       # replace with actual app URL
        app_note  = "Log in to your 5PointCredit account to view the full analysis."
        btn_color = "#2563EB"

    subject = f"✅ Your BSA Report is Ready | Ref: {reference_id}"

    body = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
    <body style="margin:0;padding:0;background-color:#F3F4F6;font-family:'Segoe UI',Arial,sans-serif;">

      <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#F3F4F6;padding:40px 0;">
        <tr>
          <td align="center">
            <table width="560" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:12px;overflow:hidden;
                          box-shadow:0 4px 24px rgba(0,0,0,0.08);">

              <!-- Header -->
              <tr>
                <td style="background:linear-gradient(135deg,#1E3A5F 0%,#2563EB 100%);
                            padding:32px;text-align:center;">
                  <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;
                             letter-spacing:0.5px;">5PointCredit</h1>
                  <p style="margin:6px 0 0;color:#BFDBFE;font-size:13px;">
                    Bank Statement Analysis
                  </p>
                </td>
              </tr>

              <!-- Body -->
              <tr>
                <td style="padding:40px 36px 16px;text-align:center;">
                  <p style="margin:0;font-size:40px;">🎉</p>
                  <h2 style="margin:16px 0 10px;font-size:20px;color:#111827;font-weight:700;">
                    Report Generated Successfully!
                  </h2>
                  <p style="margin:0;font-size:15px;color:#6B7280;line-height:1.7;">
                    Hi <strong style="color:#374151;">{recipient_name}</strong>,<br/>
                    Your Bank Statement Analysis report has been generated successfully.
                    {app_note}
                  </p>
                </td>
              </tr>

              <!-- CTA Button -->
              <tr>
                <td style="padding:28px 36px;" align="center">
                  <a href="{app_url}"
                     style="display:inline-block;padding:14px 36px;background-color:{btn_color};
                            color:#ffffff;text-decoration:none;border-radius:8px;
                            font-size:15px;font-weight:600;letter-spacing:0.3px;">
                    {app_label} →
                  </a>
                </td>
              </tr>

              <!-- Reference note -->
              <tr>
                <td style="padding:0 36px 36px;" align="center">
                  <p style="margin:0;font-size:12px;color:#9CA3AF;line-height:1.6;">
                    Reference ID:
                    <span style="font-family:monospace;color:#6B7280;font-weight:600;">
                      {reference_id}
                    </span>
                    <br/>Please quote this in any support correspondence.
                  </p>
                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="background:#F9FAFB;padding:18px 36px;border-top:1px solid #E5E7EB;
                            text-align:center;">
                  <p style="margin:0;font-size:12px;color:#9CA3AF;">
                    © 2025 5PointCredit · Mera Merchant · This is an automated notification.
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

    return subject, body

def create_body_for_password_reset(otp):
    return f"""
    Hi,

    We received a request to reset your password.

    Your OTP is: {otp}

    ⏳ This code will expire in 10 minutes.

    If you did not request this, please ignore this email.

    Regards,  
    Team 5PointCredit
    """