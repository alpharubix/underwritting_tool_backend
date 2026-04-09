import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
load_dotenv()
import os


def create_smtp_connection():
    try:
            smtp = smtplib.SMTP('smtp.zoho.com', 587, timeout=10)
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            app_password = os.getenv("APP_PASSWORD")
            smtp.login('techmgr@meramerchant.com', app_password)
            print("SMTP connection created successfully.")
            return smtp
    except Exception as e:
        print("Error creating SMTP connection:", e)
        return None


def send_mail(to, subject, body):
    try:
        smtp = create_smtp_connection()
        msg = MIMEMultipart()
        msg['From'] = "5pointcredit.com <techmgr@meramerchant.com>"
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html'))
        smtp.send_message(msg)
        smtp.quit()
        print(f"Email sent successfully to {to}")
    except Exception as e:
            print(f"Error sending email to {to}:", e)
            return None
