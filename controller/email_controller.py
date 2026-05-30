import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()
import os


def create_smtp_connection():
    try:
        smtp = smtplib.SMTP_SSL('smtp.zoho.in', 465, timeout=10)  # SMTP_SSL for port 465
        smtp.ehlo()
        app_password = os.getenv("EMAIL_APP_PASSWORD")
        smtp.login("system@5pointcredit.com", app_password)
        print("SMTP connection created successfully.")
        return smtp
    except Exception as e:
        print("Error creating SMTP connection:", e)
        return None


def send_mail(to, subject, body):
    try:
        smtp = create_smtp_connection()
        msg = MIMEMultipart()
        msg['From'] = "system@5pointcredit.com"
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        smtp.send_message(msg)
        smtp.quit()
        print(f"Email sent successfully to {to}")
    except Exception as e:
            print(f"Error sending email to {to}:", e)
            return None

