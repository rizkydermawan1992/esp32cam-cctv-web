import paho.mqtt.client as mqtt
import json

# Callback saat berhasil terhubung ke broker MQTT
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Terhubung ke broker MQTT.")
        # Subscribe ke topik yang digunakan ESP32-CAM untuk mengirim data JSON
        client.subscribe("esp32cam/sensor_data")
    else:
        print(f"Gagal terhubung. Kode error: {rc}")

# Callback saat pesan diterima dari topik yang di-subscribe
def on_message(client, userdata, msg):
    try:
        print(f"Pesan diterima di topik {msg.topic}:")
        # Decode payload JSON
        payload = msg.payload.decode("utf-8")
        data = json.loads(payload)
        
        # Ekstrak parameter dari JSON
        camera_id = data.get("camera_id")
        sensor_value = data.get("sensor_value")
        
        # Tampilkan hasil
        print(f"Camera ID: {camera_id}, Sensor Value: {sensor_value}")
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON: {e}")
    except Exception as e:
        print(f"Error: {e}")

# Konfigurasi client MQTT
broker_address = "broker.emqx.io"  # Ganti dengan alamat broker MQTT Anda
broker_port = 1883                   # Port default untuk MQTT

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Hubungkan ke broker MQTT
print("Menghubungkan ke broker MQTT...")
client.connect(broker_address, broker_port, 60)

# Jalankan loop untuk menunggu pesan masuk
try:
    client.loop_forever()
except KeyboardInterrupt:
    print("\nProgram dihentikan.")
