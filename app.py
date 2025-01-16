from flask import Flask, jsonify, render_template, request, redirect, flash, url_for, session
import json
import requests
import os
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import paho.mqtt.client as mqtt

app = Flask(__name__)
app.secret_key = "rizkyproject_05061992"


CONFIG_FILE = "config.json"
if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as file:
        json.dump({"livecam": {"esp32cams": []}, "login": {}, "telegram": {}}, file)

def read_config():
    with open(CONFIG_FILE, 'r') as file:
        return json.load(file)

def write_config(data):
    with open(CONFIG_FILE, 'w') as file:
        json.dump(data, file, indent=4)

# Callback ketika terhubung ke broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT Broker!")
    else:
        print(f"Failed to connect, return code {rc}")

# Callback ketika pesan berhasil diterbitkan
def on_publish(client, userdata, mid):
    print("Message published.")

config = read_config()
stored_email = config.get("login", {}).get("email")
stored_password_hash = config.get("login", {}).get("password")
telegram_config = config.get("telegram", {})

mqtt_config = config['mqtt']
BROKER = mqtt_config['broker']
PORT = mqtt_config['port']

# Inisialisasi MQTT Client
client = mqtt.Client()
client.on_connect = on_connect
client.on_publish = on_publish

# Hubungkan ke broker
client.connect(BROKER, PORT, 60)

def send_pan_tilt(topic):
    config = read_config()

    # Cari ESP32CAM yang sesuai dengan topik
    esp32cam = None
    for cam in config['livecam']['esp32cams']:
        if cam['topic'] == topic:
            esp32cam = cam
            break

    if esp32cam is None:
        print(f"ESP32CAM with topic {topic} not found!")
        return

    # Ambil data pan dan tilt dari config.json sesuai dengan topik
    pan = esp32cam['servo_position']['pan']
    tilt = esp32cam['servo_position']['tilt']

    # Format data JSON untuk dikirim
    data = {
        'pan': pan,
        'tilt': tilt
    }

    # Kirim data ke topik MQTT
    result = client.publish(topic, json.dumps(data))

    # Periksa hasil pengiriman
    status = result.rc
    if status == 0:
        print(f"Data {data} sent to topic {topic}")
    else:
        print(f"Failed to send message to topic {topic}")
       
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
    try:
        # Konversi ID ke integer
        data["id"] = int(data["id"])
    except ValueError:
        return redirect(url_for('livecam'))

    # Baca konfigurasi
    config = read_config()

    # Periksa apakah Camera ID sudah ada
    if any(cam["id"] == data["id"] for cam in config["livecam"]["esp32cams"]):
        return jsonify({"status": "danger", "message": "camera ID already exists!"})
    
    # Periksa apakah topic sudah ada
    if any(cam["topic"] == data["topic"] for cam in config["livecam"]["esp32cams"]):
        return jsonify({"status": "danger", "message": "Topic already exists!"})

    # Tambahkan kamera baru ke konfigurasi
    data["servo_position"] = {"pan": 90, "tilt": 90}
    config["livecam"]["esp32cams"].append(data)
    write_config(config)

    return jsonify({"status": "success", "message": "Camera added successfully!"})

@app.route("/update-camera", methods=["POST"])
def update_camera():
    data = request.get_json()
    try:
        # Konversi ID ke integer
        data["id"] = int(data["id"])
    except ValueError:
        return redirect(url_for('livecam'))

    # Baca konfigurasi
    config = read_config()
    esp32cams = config.get("livecam", {}).get("esp32cams", [])

    # Cari kamera berdasarkan ID
    camera = next((cam for cam in esp32cams if cam["id"] == data["id"]), None)
    if not camera:
        return redirect(url_for('livecam'))

    # Perbarui atribut kamera
    allowed_fields = {"label", "ip_address", "topic", "servo_position"}
    for key, value in data.items():
        if key in allowed_fields:
            camera[key] = value

    # Simpan konfigurasi
    write_config(config)

    return jsonify({"status": "success", "message": "Camera added successfully!"})


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
        return redirect(url_for('livecam'))

    # Hapus kamera dari daftar
    del esp32cams[index]
    write_config(config)  # Perbarui file konfigurasi
    return jsonify({"status": "success", "message": "Camera deleted successfully!"})


@app.route('/delete_image', methods=['POST'])
def delete_image():
    file_path = os.path.join(app.static_folder, request.form['filename'])
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({"status": "success", "message": "Image deleted successfully!"})
    else:
        return redirect(url_for('gallery'))


@app.route('/update-servo-position', methods=['POST'])
def update_servo_position():
    data = request.json
    config = read_config()
    for cam in config["livecam"]["esp32cams"]:
        if cam["id"] == data["id"]:
            cam["servo_position"][data["type"]] = data["value"]
            topic = cam["topic"]
            break
    write_config(config)
    send_pan_tilt(topic)
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
    # Jalankan server Flask
    app.run(host='0.0.0.0', port=5000)
    