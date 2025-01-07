from flask import Flask, render_template, request, redirect, flash, url_for, session
import json
import requests
import os
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Ganti dengan kunci rahasia Anda

# Load file config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)
    stored_email = config.get("login", {}).get("email")
    stored_password_hash = config.get("login", {}).get("password")
    telegram_token = config.get("telegram", {}).get("token_telegram")
    telegram_chat_id = config.get("telegram", {}).get("chat_id")
    isActiveNotification = config.get("telegram", {}).get("isActive")


@app.route("/")
def home():
    if "logged_in" in session:
        return redirect(url_for("livecam"))
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    # Validasi email dan password dengan hashing
    if email == stored_email and check_password_hash(stored_password_hash, password):
        session["logged_in"] = True
        session["user_email"] = email
        flash("Login successful!", "success")
        return redirect(url_for("livecam"))
    else:
        flash("Invalid email or password. Please try again.", "danger")
        return redirect(url_for("home"))

@app.route("/livecam")
def livecam():
    if "logged_in" not in session:
        flash("Please log in to access the Live Cam.", "warning")
        return redirect(url_for("home"))
    return render_template("livecam.html", user_email=session["user_email"])

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("user_email", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/gallery")
def gallery():
    if "logged_in" not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("home"))

    # Path ke direktori static/uploads
    upload_folder = os.path.join(app.static_folder, "uploads")

    # Ambil daftar file di folder uploads, urutkan dari yang terbaru
    images_with_timestamps = []
    if os.path.exists(upload_folder):
        images = [file for file in os.listdir(upload_folder) if file.lower().endswith(('png', 'jpg', 'jpeg', 'gif'))]
        images.sort(key=lambda x: os.path.getmtime(os.path.join(upload_folder, x)), reverse=True)

        # Tambahkan data timestamp untuk setiap gambar
        for image_file in images:
            file_path = os.path.join(upload_folder, image_file)
            timestamp = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M:%S")
            images_with_timestamps.append({
                "filename": os.path.join("uploads/", image_file),
                "timestamp": timestamp
            })

    # Kirim daftar file dan timestamp ke template
    return render_template("gallery.html", images=images_with_timestamps)

@app.route("/setting")
def setting():
    if "logged_in" not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("home"))
    return render_template("setting.html")

@app.route("/form")
def form():
    return render_template("form.html")

@app.route("/send_message", methods=["POST"])
def send_message():
    if isActiveNotification == 0:
        flash("Telegram notifications are disabled.", "warning")
        return redirect(url_for("home"))

    # Ambil pesan dari form
    # message = request.form["message"]
    message = "Motion Detected!!!"

    # Ambil file gambar dari form
    image = request.files.get("imageFile")

    if image:
        # Simpan gambar ke direktori lokal dengan nama file unik berbasis timestamp
        upload_folder = "static/uploads"
        os.makedirs(upload_folder, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        unique_filename = f"{timestamp}_{secure_filename(image.filename)}"
        image_path = os.path.join(upload_folder, unique_filename)
        image.save(image_path)

        # Kirim gambar ke Telegram
        url = f"https://api.telegram.org/bot{telegram_token}/sendPhoto"
        payload = {
            "chat_id": telegram_chat_id,
            "caption": message
        }
        with open(image_path, "rb") as file:
            files = {"photo": (unique_filename, file, image.mimetype)}
            response = requests.post(url, data=payload, files=files)
    else:
        # Kirim pesan teks ke Telegram jika tidak ada gambar
        url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        payload = {
            "chat_id": telegram_chat_id,
            "text": message
        }
        response = requests.post(url, data=payload)

    # Tampilkan notifikasi berdasarkan hasil pengiriman
    if response.status_code == 200:
        flash("Message sent to Telegram successfully!", "success")
    else:
        flash("Failed to send message to Telegram.", "danger")

    return redirect(url_for("home"))

@app.route('/delete_image', methods=['POST'])
def delete_image():
    filename = request.form['filename']
    file_path = os.path.join(app.static_folder, filename)
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            flash('Image deleted successfully!', 'success')
        else:
            flash('File not found.', 'error')
    except Exception as e:
        flash(f'An error occurred: {e}', 'error')
    return redirect(url_for('gallery'))  # Redirect ke halaman gallery


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
