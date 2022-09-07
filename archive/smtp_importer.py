from os import environ
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

load_dotenv()
#load_dotenv()
# Be sur to add to path before starting server
USER_EMAIL_ADDRESS = environ.get("EMAIL")
EMAIL_PASSWORD = environ.get("PASSWORD")


def submit_email(body, subject, to_list, ):
    # Might change this so that the target email is passed via the view
    email_list_result_test = to_list #must be an array
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = USER_EMAIL_ADDRESS
    message["To"] = ", ".join(email_list_result_test)

    s = smtplib.SMTP("smtp.office365.com", 587)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(USER_EMAIL_ADDRESS, EMAIL_PASSWORD)
    html = MIMEText(body, "html")
    # plain = MIMEText('your email program is too old', 'plain')

    # message.attach(plain)
    message.attach(html)

    s.sendmail(message["From"], email_list_result_test, message.as_string())
    s.quit()

submit_email("Test", "Test")

"""
set script to send emails with attached excel files to:
commitment invoice updates
commitments
companies
"""