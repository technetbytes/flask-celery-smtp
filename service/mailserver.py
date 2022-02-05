from pyexpat.errors import messages
import yaml
from flask import Flask, request, render_template, session, flash, redirect, url_for
from celerycontext import make_celery
import smtplib , ssl

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def get_configuration():
    # Read YAML configuration file
    with open("config.yml","r") as ymlfile:
        cfg = yaml.safe_load(ymlfile)
    return cfg

def init_smtp_server(config):
    try:
        # Initialize smtp server
        print(" init smtp server")
        sender_email = config['smtp_server']['username']
        sender_pass = config['smtp_server']['password']
        smtp_server = smtplib.SMTP_SSL(config['smtp_server']['gateway'], config['smtp_server']['port'])
        smtp_server.ehlo() # Can be omitted, To identify yourself to the server
        smtp_server.login(sender_email, sender_pass)
        print("Login in smtp server ...")
    except Exception as e:
        # Print any error messages to stdout
        print("error :- ",e)
    return smtp_server


def build_message(email_info, from_address):
    message = MIMEMultipart("alternative")
    message["Subject"] = email_info["subject"]
    message["From"] = from_address
    message["To"] = email_info["to"]
    body = MIMEText(email_info["body"], "html")
    message.attach(body)
    return message

# Flask application
flask_app = Flask(__name__)
smtp_server = None

#Read configuration config.yml
config = get_configuration()

# Set application secret_key
flask_app.config['SECRET_KEY'] = config['others']['secret_key']
flask_app.config['SEND_INFO'] = config['email']['sender']

# Initialize object
celery = make_celery(flask_app)

@celery.task
def send_async_email(email_info):
    print("Start sending email")
    # Create a secure SSL context
    context = ssl.create_default_context()
    try:
        message = build_message(email_info, flask_app.config['SEND_INFO'])
        smtp_server = init_smtp_server(config)
        print(smtp_server)
        print("message sent ....")
        smtp_server.send_message(message)
    except Exception as e:
        # Print any error messages to stdout
        print("error :- ",e)

@flask_app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html', email=session.get('email', ''))
    email = request.form['email']
    subject = request.form['subject']
    email_body = request.form['body']
    session['email'] = email

    # send the email
    email_data = {
        'subject': subject,
        'to': email,
        'body': email_body
    }
    if request.form['submit'] == 'Send':
        # send right away
        send_async_email.delay(email_data)
        flash('Sending email to {0}'.format(email))

    return redirect(url_for('index'))


if __name__ == '__main__':
    # run application
    flask_app.run(debug=True)