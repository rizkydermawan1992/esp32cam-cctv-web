from flask import Flask, jsonify, render_template, request, redirect, flash, url_for, session
import json
import requests
import os
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"

CONFIG_FILE = "config.json"
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as file:
        json.dump({"livecam": {"esp32cams": []}, "login": {}, "telegram": {}}, file)

# Helper functions
def read_config():
    with open(CONFIG_FILE, 'r') as file:
        return json.load(file)

def write_config(data):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(data, file, indent=4)

config = read_config()
stored_email = config.get("login", {}).get("email")
stored_password_hash = config.get("login", {}).get("password")
telegram_config = config.get("telegram", {})

@app.route("/")
def home():
    return redirect(url_for("livecam")) if "logged_in" in session else render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    email, password = request.form["email"], request.form["password"]
    if email == stored_email and check_password_hash(stored_password_hash, password):
        session.update({"logged_in": True, "user_email": email})
        flash("Login successful!", "success")
        return redirect(url_for("livecam"))
    flash("Invalid email or password.", "danger")
    return redirect(url_for("home"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("home"))

@app.route("/livecam")
def livecam():
    if "logged_in" not in session:
        flash("Please log in to access the Live Cam.", "warning")
        return redirect(url_for("home"))
    return render_template("livecam.html", user_email=session["user_email"])

@app.route('/get-livecam-data')
def get_livecam_data():
    return jsonify(read_config()["livecam"]["esp32cams"])

@app.route("/add-camera", methods=["POST"])
def add_camera():
    data = request.get_json()

    # Periksa field yang hilang
    if not all(k in data for k in ("id", "label", "ip_address", "topic")):
        flash("Missing required fields!", "danger")
        return redirect(url_for('livecam'))  # Redirect ke halaman utama jika ada kesalahan

    try:
        # Konversi ID ke integer
        data["id"] = int(data["id"])
    except ValueError:
        flash("ID must be a numeric value!", "danger")
        return redirect(url_for('livecam'))

    # Baca konfigurasi
    config = read_config()

    # Periksa apakah ID sudah ada
    if any(cam["id"] == data["id"] for cam in config["livecam"]["esp32cams"]):
        flash("Camera ID already exists!", "danger")
        return redirect(url_for('livecam'))

    # Tambahkan kamera baru ke konfigurasi
    data["servo_position"] = {"pan": 90, "tilt": 90}
    config["livecam"]["esp32cams"].append(data)
    write_config(config)

    # Flash message untuk sukses
    flash("Camera added successfully.", "success")
    return redirect(url_for('livecam'))



@app.route("/gallery")
def gallery():
    if "logged_in" not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("home"))

    upload_folder = os.path.join(app.static_folder, "uploads")
    images_with_timestamps = []

    if os.path.exists(upload_folder):
        images = sorted((f for f in os.listdir(upload_folder) if f.lower().endswith(('png', 'jpg', 'jpeg', 'gif'))),
                        key=lambda x: os.path.getmtime(os.path.join(upload_folder, x)), reverse=True)
        for image_file in images:
            file_path = os.path.join(upload_folder, image_file)
            timestamp = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
            images_with_timestamps.append({"filename": f"uploads/{image_file}", "timestamp": timestamp})

    return render_template("gallery.html", images=images_with_timestamps)

@app.route('/delete_camera/<int:cam_id>', methods=['GET'])
def delete_camera(cam_id):
    cam_id = int(cam_id)
    config = read_config()
    esp32cams = config.get("livecam", {}).get("esp32cams", [])

    # Cari indeks kamera berdasarkan ID
    index = next((i for i, cam in enumerate(esp32cams) if cam["id"] == cam_id), None)
    
    if index is None:
        flash("Camera not found.", "danger")
        return redirect(url_for('livecam'))

    # Hapus kamera dari daftar
    del esp32cams[index]
    write_config(config)  # Perbarui file konfigurasi

    flash("Camera deleted successfully.", "success")
    return redirect(url_for('livecam'))


@app.route('/delete_image', methods=['POST'])
def delete_image():
    file_path = os.path.join(app.static_folder, request.form['filename'])
    if os.path.exists(file_path):
        os.remove(file_path)
        flash('Image deleted successfully!', 'success')
    else:
        flash('File not found.', 'error')
    return redirect(url_for('gallery'))


@app.route('/update-servo-position', methods=['POST'])
def update_servo_position():
    data = request.json
    config = read_config()
    for cam in config["livecam"]["esp32cams"]:
        if cam["id"] == data["id"]:
            cam["servo_position"][data["type"]] = data["value"]
            break
    write_config(config)
    return jsonify({'status': 'success', 'message': 'Config updated successfully'})

@app.route("/send_message", methods=["POST"])
def send_message():
    if telegram_config.get("isActive") == 0:
        flash("Telegram notifications are disabled.", "warning")
        return redirect(url_for("home"))

    message = "Motion Detected!!!"
    image = request.files.get("imageFile")
    if image:
        upload_folder = os.path.join("static", "uploads")
        os.makedirs(upload_folder, exist_ok=True)
        unique_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{secure_filename(image.filename)}"
        image_path = os.path.join(upload_folder, unique_filename)
        image.save(image_path)

        url = f"https://api.telegram.org/bot{telegram_config['token_telegram']}/sendPhoto"
        with open(image_path, "rb") as file:
            response = requests.post(url, data={"chat_id": telegram_config["chat_id"], "caption": message},
                                     files={"photo": (unique_filename, file, image.mimetype)})
    else:
        url = f"https://api.telegram.org/bot{telegram_config['token_telegram']}/sendMessage"
        response = requests.post(url, data={"chat_id": telegram_config["chat_id"], "text": message})

    flash("Message sent successfully!" if response.status_code == 200 else "Failed to send message.",
          "success" if response.status_code == 200 else "danger")
    return redirect(url_for("home"))

@app.route("/setting")
def setting():
    if "logged_in" not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("home"))
    return render_template("setting.html")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
