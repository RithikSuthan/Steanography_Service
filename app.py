import numpy as np
from flask import Flask, jsonify, request, send_file,send_from_directory
import random
from pymongo import MongoClient
from stegano import lsb  # Use the stegano library for embedding messages in images
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from PIL import Image
import os
import base64
import io
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# MongoDB connection
mongo_client = MongoClient("mongodb+srv://Rithik_Suthan_S:8098329762@cluster0.nwyrzl2.mongodb.net/steanography")
db = mongo_client["steanography"]
users_collection = db["users"]
photos_collection = db["photos"]

# Email configurations
SENDER_EMAIL = "rithikmanagement@gmail.com"
EMAIL_PASSWORD = "pjjn laiz iqvb ybbd"  # Use environment variables for better security


@app.route('/sendotp', methods=['POST'])
def send_email_route():
    # Generate a random OTP
    rn = random.randrange(100000, 1000000)
    print(f"Generated OTP: {rn}")

    data = request.get_json()
    send_to_email = data.get('send_to_email')
    name = data.get('name')

    # Ensure all required fields are present
    if not send_to_email or not name:
        return jsonify({"message": "Email and name are required"}), 400

    subject = "OTP Verification"
    original_image = "E:\\9th Semester\\IS Project\\Image Based Authentication System\\uploads\\apple.jpg"
    otp_image = "otp_image.png"

    # Embed the OTP into the image
    otp_message = str(rn)
    try:
        otp_embedded_image = lsb.hide(original_image, otp_message)
        otp_embedded_image.save(otp_image)
    except Exception as e:
        return jsonify({"message": f"Failed to embed OTP: {str(e)}"}), 500

    # Send the OTP-embedded image via email
    result = send_email_with_image(SENDER_EMAIL, send_to_email, subject,
                                   f"Hi {name}, here is your OTP embedded image.", otp_image)

    return jsonify({"message": result, "otp": str(rn)}), 200


def send_email_with_image(sender_email, send_to_email, subject, message, image_path):
    # Set up the email
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = send_to_email
    msg['Subject'] = subject

    # Attach the message body
    msg.attach(MIMEText(message, 'plain'))

    # Attach the image file
    try:
        with open(image_path, 'rb') as attachment:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename={os.path.basename(image_path)}",
            )
            msg.attach(part)
    except Exception as e:
        return f"Failed to attach image: {str(e)}"

    # Set up the email server
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, EMAIL_PASSWORD)
        server.sendmail(sender_email, send_to_email, msg.as_string())
        return "OTP image sent successfully"
    except Exception as e:
        return f"Failed to send OTP image: {str(e)}"
    finally:
        server.quit()


@app.route('/verifyotp', methods=['POST'])
def verify_otp_route():
    if 'file' not in request.files or 'otp' not in request.form or 'email' not in request.form:
        return jsonify({"message": "File, OTP, and email are required"}), 400

    file = request.files['file']
    original_otp = request.form['otp']
    email = request.form['email']

    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400

    # Save and extract OTP from the uploaded image
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(image_path)

    try:
        extracted_otp = extract_otp_from_image(image_path)
    except Exception as e:
        return jsonify({"message": f"Failed to extract OTP: {str(e)}"}), 500

    # Verify OTP
    if extracted_otp == original_otp:
        return jsonify({"message": "OTP verification successful"}), 200
    else:
        return jsonify({"message": "OTP verification failed"}), 400


def extract_otp_from_image(image_path):
    try:
        # Extract hidden OTP using stegano
        hidden_otp = lsb.reveal(image_path)
        return hidden_otp
    except Exception as e:
        raise Exception(f"Error extracting OTP: {str(e)}")


@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()

    name = data.get('name')
    email = data.get('email')
    friends = data.get('friends')
    password = data.get('password')

    # Ensure required fields are present
    if not name or not email or not password:
        return jsonify({"message": "Name, email, and password are required"}), 400

    existing_user = users_collection.find_one({"email": email})
    if existing_user:
        return jsonify({"message": "User already exists"}), 409  # Conflict

    new_user = {
        "name": name,
        "email": email,
        "friends": friends,
        "password": password
    }

    users_collection.insert_one(new_user)
    return jsonify({"message": "User registered successfully!"}), 201  # Created


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    existing_user = users_collection.find_one({"email": email, "password": password})
    if existing_user:
        return jsonify({"message": "Login successful."}), 200
    else:
        return jsonify({"message": "Invalid email or password"}), 401


original_images = r'E:\9th Semester\IS Project\Image Based Authentication System\original_images'
shares = 'shares'
os.makedirs(original_images, exist_ok=True)  # Create the folder if it doesn't exist
os.makedirs(shares, exist_ok=True)

def split_image(image):
    image_array = np.array(image)
    share1 = np.random.randint(0, 2, size=image_array.shape, dtype=np.uint8)
    share2 = (image_array - share1) % 2
    return share1, share2

def encode_image(share, quality=85):
    """Compresses and encodes the image share to bytes."""
    pil_img = Image.fromarray(np.uint8(share * 255))
    buf = io.BytesIO()
    # Save the image with compression
    pil_img.save(buf, format="JPEG", quality=quality)  # Use JPEG format for compression
    byte_im = buf.getvalue()
    return byte_im  # Return raw bytes instead of base64 encoded string

@app.route('/upload', methods=['POST'])
def upload_photo():
    data = request.form
    email = data.get('email')
    photo_name = data.get('photo_name')

    # Check if a file is provided
    if 'file' not in request.files:
        return jsonify({"message": "No file part."}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"message": "No selected file."}), 400

    try:
        image = Image.open(file)
    except Exception as e:
        return jsonify({"message": f"Failed to open image: {str(e)}"}), 400

    # Save the original image
    original_path = os.path.join(original_images, f"{email}_{photo_name}.jpg")
    try:
        image.save(original_path)
    except Exception as e:
        return jsonify({"message": f"Failed to save original photo: {str(e)}"}), 500

    # Split image into shares
    share1, share2 = split_image(image)

    # Encode shares to bytes with compression
    byte_share1 = encode_image(share1)
    byte_share2 = encode_image(share2)

    # Generate file paths for the shares
    share1_path = os.path.join(shares, f"{email}_{photo_name}_share1.jpg")
    share2_path = os.path.join(shares, f"{email}_{photo_name}_share2.jpg")

    # Save the shares to local filesystem
    try:
        with open(share1_path, 'wb') as f:
            f.write(byte_share1)
        with open(share2_path, 'wb') as f:
            f.write(byte_share2)
    except Exception as e:
        return jsonify({"message": f"Failed to save shares: {str(e)}"}), 500

    return jsonify({"message": "Photo uploaded successfully."}), 200

@app.route('/get_photo', methods=['GET'])
def get_photo():
    email = request.args.get('email')
    photo_name = request.args.get('photo_name')

    # Generate file paths for the original photo and shares
    original_path = os.path.join(original_images, f"{email}_{photo_name}.jpg")
    share1_path = os.path.join(shares, f"{email}_{photo_name}_share1.jpg")
    share2_path = os.path.join(shares, f"{email}_{photo_name}_share2.jpg")

    # Check if the original photo exists
    if os.path.exists(original_path):
        return send_file(original_path, mimetype='image/jpeg')

    # If the original doesn't exist, check for shares
    if os.path.exists(share1_path) and os.path.exists(share2_path):
        return jsonify({
            "message": "Shares found, original not available.",
            "shares": {
                "share1": share1_path,
                "share2": share2_path
            }
        }), 200

    return jsonify({"message": "Photo not found."}), 404

@app.route('/delete', methods=['POST'])
def delete_photo():
    data = request.get_json()
    email = data.get('email')
    photo_name = data.get('photo_name')

    # Generate file paths for the shares and the original photo
    original_path = os.path.join(original_images, f"{email}_{photo_name}.jpg")
    share1_path = os.path.join(shares, f"{email}_{photo_name}_share1.jpg")
    share2_path = os.path.join(shares, f"{email}_{photo_name}_share2.jpg")

    # Attempt to delete the files
    try:
        os.remove(original_path)
        os.remove(share1_path)
        os.remove(share2_path)
    except FileNotFoundError:
        return jsonify({"message": "Photo not found."}), 404
    except Exception as e:
        return jsonify({"message": f"Failed to delete photo: {str(e)}"}), 500

    return jsonify({"message": "Photo deleted successfully."}), 200


@app.route('/get_images', methods=['GET'])
def get_images():
    email = request.args.get('email')
    images = []

    print(f"Fetching images for email: {email}")  # Log email being processed
    print(f"Searching in folder: {original_images}")  # Log folder being searched

    for filename in os.listdir(original_images):
        print(f"Processing filename: {filename}")  # Log each filename being processed

        if filename.startswith(email):  # Check if filename starts with the email
            try:
                base_name, ext = os.path.splitext(filename)  # Split filename from its extension
                parts = base_name.split('_')  # Split the base name by '_'

                # Ensure there are enough parts to access
                if len(parts) == 2 and parts[0] == email:
                    photo_name = parts[1]  # Extract photo_name from filename
                    images.append({
                        "photo_name": photo_name,
                        "url": f"/images/{filename}"  # URL to access the original image
                    })
                else:
                    print(f"Filename {filename} does not have the expected format. Parts found: {parts}")

            except Exception as e:
                print(f"Error processing filename {filename}: {e}")

    return jsonify(images), 200


@app.route('/images/<path:filename>', methods=['GET'])
def get_image(filename):
    # Serve the requested image from the specified directory
    return send_from_directory(original_images, filename)

if __name__ == '__main__':
    app.run(debug=True)

