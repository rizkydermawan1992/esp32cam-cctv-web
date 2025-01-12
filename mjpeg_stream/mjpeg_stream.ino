#include "OV2640.h"
#include <WiFi.h>
#include <WebServer.h>
#include <WiFiClient.h>
#include <PubSubClient.h> // Library untuk MQTT
#include <ESP32Servo.h>        // Library untuk kontrol servo
#include <ArduinoJson.h>  // Library untuk parsing JSON

// Pilih model kamera
#define CAMERA_MODEL_AI_THINKER
#include "camera_pins.h"

#define SSID1 "Realme"
#define PWD1 "12345678"

// Informasi broker MQTT
#define MQTT_BROKER "broker.emqx.io"
#define MQTT_PORT 1883
#define MQTT_TOPIC "esp32cam" // Topik untuk publish
#define MQTT_SUB_TOPIC "esp32cam/292jdq" // Topik untuk subscribe

byte cam_id = 1; // ID Kamera
OV2640 cam;
WebServer server(80);
WiFiClient espClient;
PubSubClient client(espClient); // MQTT client

Servo panServo;
Servo tiltServo;

// Pin servo
#define PAN_SERVO_PIN 14
#define TILT_SERVO_PIN 15

// Posisi awal servo
int panPosition = 90;
int tiltPosition = 90;

const char JHEADER[] = "HTTP/1.1 200 OK\r\n"
                       "Content-disposition: inline; filename=capture.jpg\r\n"
                       "Content-type: image/jpeg\r\n\r\n";

const char HEADER[] = "HTTP/1.1 200 OK\r\n"
                      "Access-Control-Allow-Origin: *\r\n"
                      "Content-Type: multipart/x-mixed-replace; boundary=123456789000000000000987654321\r\n";
const char BOUNDARY[] = "\r\n--123456789000000000000987654321\r\n";
const char CTNTTYPE[] = "Content-Type: image/jpeg\r\nContent-Length: ";
const int hdrLen = strlen(HEADER);
const int bdrLen = strlen(BOUNDARY);
const int cntLen = strlen(CTNTTYPE);

void handle_jpg_stream(void) {
  char buf[32];
  int s;

  WiFiClient client = server.client();

  client.write(HEADER, hdrLen);
  client.write(BOUNDARY, bdrLen);

  while (true) {
    if (!client.connected())
      break;
    cam.run();
    s = cam.getSize();
    client.write(CTNTTYPE, cntLen);
    sprintf(buf, "%d\r\n\r\n", s);
    client.write(buf, strlen(buf));
    client.write((char *)cam.getfb(), s);
    client.write(BOUNDARY, bdrLen);
  }
}

void handle_jpg(void) {
  WiFiClient client = server.client();

  cam.run();
  if (!client.connected())
    return;

  client.write(JHEADER, strlen(JHEADER));
  client.write((char *)cam.getfb(), cam.getSize());
}

void handleNotFound() {
  String message = "Server is running!\n\n";
  message += "URI: ";
  message += server.uri();
  message += "\nMethod: ";
  message += (server.method() == HTTP_GET) ? "GET" : "POST";
  message += "\nArguments: ";
  message += server.args();
  message += "\n";
  server.send(200, "text/plain", message);
}

void mqtt_callback(char *topic, byte *message, unsigned int length) {
  String messageTemp;
  for (int i = 0; i < length; i++) {
    messageTemp += (char)message[i];
  }

  if (String(topic) == MQTT_SUB_TOPIC) {
//    Serial.print("Received JSON message: ");
//    Serial.println(messageTemp);

    // Parse JSON
    StaticJsonDocument<256> doc;
    DeserializationError error = deserializeJson(doc, messageTemp);
    if (error) {
      Serial.print("Failed to parse JSON: ");
      Serial.println(error.f_str());
      return;
    }

    // Ambil nilai pan dan tilt dari JSON
    if (doc.containsKey("pan") && doc.containsKey("tilt")) {
      panPosition = doc["pan"];
      tiltPosition = doc["tilt"];

//      // Pastikan nilai dalam rentang servo
      panPosition = constrain(panPosition, 0, 180);
      tiltPosition = constrain(tiltPosition, 0, 180);

//      // Atur posisi servo
      panServo.write(panPosition);
      tiltServo.write(tiltPosition);

      Serial.print("Updated pan: ");
      Serial.print(panPosition);
      Serial.print(", tilt: ");
      Serial.println(tiltPosition);
    } else {
      Serial.println("Invalid JSON format: Missing pan or tilt key");
    }
  }
}

void reconnect_mqtt() {
  while (!client.connected()) {
    Serial.println("Connecting to MQTT Broker...");
    if (client.connect("ESP32Cam")) {
      Serial.println("MQTT connected");
      client.subscribe(MQTT_SUB_TOPIC);
    } else {
      Serial.print("Failed to connect, retrying in 5 seconds. Error code: ");
      Serial.println(client.state());
      delay(5000);
    }
  }
}

void mqttTask(void *param) {
  while (true) {
    if (!client.connected()) {
      reconnect_mqtt();
    }
    client.loop();
    vTaskDelay(10 / portTICK_PERIOD_MS); // Task delay untuk CPU time slice
  }
}

void mjpegTask(void *param) {
  while (true) {
    server.handleClient();
    vTaskDelay(10 / portTICK_PERIOD_MS); // Task delay untuk CPU time slice
  }
}

void setup() {
  Serial.begin(115200);

  // Setup servo
  panServo.attach(PAN_SERVO_PIN);
  tiltServo.attach(TILT_SERVO_PIN);
  panServo.write(panPosition);
  tiltServo.write(tiltPosition);

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 12;
  config.fb_count = 2;

  cam.init(config);

  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID1, PWD1);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(F("."));
  }
  Serial.println(F("\nWiFi connected"));
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  client.setServer(MQTT_BROKER, MQTT_PORT);
  client.setCallback(mqtt_callback);

  server.on("/mjpeg/1", HTTP_GET, handle_jpg_stream);
  server.on("/jpg", HTTP_GET, handle_jpg);
  server.onNotFound(handleNotFound);
  server.begin();

  xTaskCreatePinnedToCore(mqttTask, "MQTT Task", 4096, NULL, 1, NULL, 0);
  xTaskCreatePinnedToCore(mjpegTask, "MJPEG Task", 8192, NULL, 1, NULL, 1);
}

void loop() {
  // Tidak ada logic di loop utama
}
