#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>
#include <Adafruit_INA219.h>
#include <SD.h>
#include <SPI.h>

#define SD_CS 13

const char* ssid = "WIFI_SSID";
const char* password = "WIFI_PASSWORD";

IPAddress gatewayIp(192, 168, 1, 100);
const int gatewayPort = 5005;

WiFiUDP udp;
Adafruit_INA219 ina219;

const int NODE_ID = 1;
const int TRIAL_ID = 1;

//keiciam pagal scenariju
const int PACKET_COUNT = 300;

// 10 pps = 100 ms, 20 pps = 50 ms, 30 pps = 33 ms
const float PACKET_RATE_PPS = 20.0;
const unsigned long PACKET_INTERVAL_MS = 50;

const char* ENERGY_LOG_FILE = "/energy_log_wifi.csv";

int seq = 0;
unsigned long lastSend = 0;
unsigned long startTime = 0;

float accumulatedEnergyJ = 0.0;
unsigned long lastEnergyRead = 0;

void setup() {
  Serial.begin(115200);
  delay(1000);

  if (!ina219.begin()) {
    Serial.println("INA219 not found");
    while (true);
  }

  if (!SD.begin(SD_CS)) {
    Serial.println("SD card initialization failed");
    while (true);
  }

  File file = SD.open(ENERGY_LOG_FILE, FILE_WRITE);
  if (file) {
    file.println("packet_rate_pps,trial,seq,tx_time_ms,current_ma,voltage_v,energy_j");
    file.close();
  }

  WiFi.begin(ssid, password);

  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println();
  Serial.print("Connected. ESP32 IP: ");
  Serial.println(WiFi.localIP());

  Serial.println("seq,tx_time_ms,rssi_dbm,current_ma,voltage_v,energy_j");

  startTime = millis();
  lastEnergyRead = millis();
}

void loop() {
  unsigned long now = millis();

  unsigned long dtMs = now - lastEnergyRead;
  if (dtMs >= 100) {
    float currentMa = ina219.getCurrent_mA();
    float busVoltage = ina219.getBusVoltage_V();

    float powerW = (currentMa / 1000.0) * busVoltage;
    accumulatedEnergyJ += powerW * (dtMs / 1000.0);

    lastEnergyRead = now;
  }

  if (seq >= PACKET_COUNT) {
    return;
  }

  if (now - lastSend >= PACKET_INTERVAL_MS) {
    lastSend = now;

    int rssi = WiFi.RSSI();
    float currentMa = ina219.getCurrent_mA();
    float voltageV = ina219.getBusVoltage_V();

    char payload[160];

    snprintf(
      payload,
      sizeof(payload),
      "%02d,%03d,%08lu,%d,DATA",
      NODE_ID,
      seq,
      millis(),
      rssi
    );

    udp.beginPacket(gatewayIp, gatewayPort);
    udp.print(payload);
    udp.endPacket();

    Serial.print(seq);
    Serial.print(",");
    Serial.print(millis());
    Serial.print(",");
    Serial.print(rssi);
    Serial.print(",");
    Serial.print(currentMa);
    Serial.print(",");
    Serial.print(voltageV);
    Serial.print(",");
    Serial.println(accumulatedEnergyJ, 6);

    File file = SD.open(ENERGY_LOG_FILE, FILE_APPEND);
    if (file) {
      file.print(PACKET_RATE_PPS);
      file.print(",");
      file.print(TRIAL_ID);
      file.print(",");
      file.print(seq);
      file.print(",");
      file.print(millis());
      file.print(",");
      file.print(currentMa);
      file.print(",");
      file.print(voltageV);
      file.print(",");
      file.println(accumulatedEnergyJ, 6);
      file.close();
    }
    seq++;
  }
}
