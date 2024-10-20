from flask import Flask, jsonify, request
import random

from pymongo import MongoClient
from stegano import lsb  # Use the stegano library for embedding messages in images
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
from flask_cors import CORS, cross_origin
app = Flask(__name__)
CORS(app)


mongo_client = MongoClient("mongodb+srv://Rithik_Suthan_S:8098329762@cluster0.nwyrzl2.mongodb.net/steanography")
db = mongo_client["steanography"]  # Replace with your database name
users_collection = db["users"]  # Collection for storing user data

@cross_origin()
@app.route('/sendotp', methods=['POST'])
def send_email_route():
    # Generate a random OTP
    rn = random.randrange(100000, 1000000)
    print(rn)
    data = request.get_json()
    sender_email = "rithikmanagement@gmail.com"
    send_to_email = data.get('send_to_email')
    subject = "OTP Verification"

    # Define the image path where the OTP will be embedded
    original_image = "E:\\9th Semester\\IS Project\\Image Based Authentication System\\uploads\\apple.jpg"
    otp_image = "otp_image.png"  # Output image with embedded OTP

    # Embed the OTP into the image using stegano (LSB steganography)
    otp_message = str(rn)  # Convert OTP to string for embedding
    otp_embedded_image = lsb.hide(original_image, otp_message)  # Embed OTP into image
    otp_embedded_image.save(otp_image)  # Save the new image with embedded OTP

    # Send the OTP-embedded image via email
    result = send_email_with_image(sender_email, send_to_email, subject,
                                   "Hi " + data.get('name') + ", here is your OTP embedded image.", otp_image)

    return jsonify({"message": result, "otp": str(rn)}), 200


def send_email_with_image(sender_email, send_to_email, subject, message, image_path):
    password = "pjjn laiz iqvb ybbd"  # Sender's email password

    # Create the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = send_to_email
    msg['Subject'] = subject

    # Attach the message body
    msg.attach(MIMEText(message, 'plain'))

    # Attach the image file
    with open(image_path, 'rb') as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {os.path.basename(image_path)}",
        )
        msg.attach(part)

    # Set up the email server
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()

    try:
        # Log in to the email account
        server.login(sender_email, password)

        # Send the email
        text = msg.as_string()
        server.sendmail(sender_email, send_to_email, text)
        return "OTP image sent successfully"
    except Exception as e:
        print(e)
        return "Failed to send OTP image"
    finally:
        server.quit()


UPLOAD_FOLDER = 'uploads/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# Route to handle image upload and OTP verification
@app.route('/verifyotp', methods=['POST'])
def verify_otp_route():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400

    if file:
        # Save the uploaded image file
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(image_path)

        # Extract the OTP from the image using Stegano
        extracted_otp = extract_otp_from_image(image_path)

        # Now verify the extracted OTP with the original one (assuming the original OTP is stored)
        original_otp = request.form['otp']  # Correctly retrieving OTP
        email = request.form['email']  # Retrieving email
        print(original_otp)
        if extracted_otp == original_otp:
            return jsonify({"message": "OTP verification successful"}), 200
        else:
            return jsonify({"message": "OTP verification failed"}), 400


# Helper function to extract OTP from image
def extract_otp_from_image(image_path):
    try:
        # Extract the hidden OTP using stegano
        hidden_otp = lsb.reveal(image_path)
        return hidden_otp
    except Exception as e:
        print(e)
        return None


from flask import request, jsonify
import random

@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()  # Get JSON data from the request

    name = data.get('name')
    email = data.get('email')
    friends = data.get('friends')  # OTP if needed
    password =data.get('password')

    # Check if user already exists
    existing_user = users_collection.find_one({"email": email})
    if existing_user:
        return jsonify({"message": "User already exists."}), 409  # Conflict

    # Create a new user document
    new_user = {
        "name": name,
        "email": email,
        "friends": friends,
        "password":password
    }

    # Insert the new user into the database
    users_collection.insert_one(new_user)

    return jsonify({"message": "User registered successfully!"}), 201  # Created


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    # Check if email and password are present in the request
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    # Query MongoDB for a user with the given email and password
    existing_user = users_collection.find_one({"email": email, "password": password})

    if existing_user:
        return jsonify({"message": "Login Successful."}), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401


if __name__ == '__main__':
    app.run(debug=True)
