from controller.email_controller import send_mail
from utils.email_utility import create_body_for_new_registration


def send_registration_mail_to_user(to,data):
    formated_body = create_body_for_new_registration(data)
    subject = "Welcome to 5PointCredit! Get Started Now 🚀"
    return send_mail(to, subject,formated_body)