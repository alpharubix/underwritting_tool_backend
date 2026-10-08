import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
loaded=load_dotenv()
import os


def create_smtp_connection():
    smtp_host = "smtp.zoho.in"
    smtp_port = 465

    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("EMAIL_APP_PASSWORD")

    if not username:
        raise ValueError("SMTP_USERNAME is not configured")

    if not password:
        raise ValueError("EMAIL_APP_PASSWORD is not configured")

    try:
        smtp = smtplib.SMTP_SSL(
            smtp_host,
            smtp_port,
            timeout=10
        )

        smtp.ehlo()

        smtp.login(username, password)

        print("SMTP authentication successful.")

        return smtp

    except smtplib.SMTPAuthenticationError as e:
        print("SMTP authentication failed:", e)
        raise

    except Exception as e:
        print("Error creating SMTP connection:", e)
        raise

# create_smtp_connection()
def send_mail(to, subject, body):
    try:
        smtp = create_smtp_connection()
        msg = MIMEMultipart()
        msg['From'] = os.getenv("SMTP_FROM")
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        smtp.send_message(msg)
        smtp.quit()
        print(f"Email sent successfully to {to}")
    except Exception as e:
            print(f"Error sending email to {to}:", e)
            return None

