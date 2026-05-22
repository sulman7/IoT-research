#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <Wire.h>
#include <Adafruit_INA219.h>
#include <SD.h>
#include <SPI.h>

#define SD_CS 13
#define SERVICE_UUID        "xxxxxxxxxxxxxxxxx"
#define CHARACTERISTIC_UUID "xxxxxxxxxxxxxxxxxxxxx"

BLECharacteristic* txCharacteristic;
Adafruit_INA219 ina219;

//keicias pagal scenariju
const int NODE_ID = 1;
const int TRIAL_ID = 1;
const int PACKET_COUNT = 300;

// 5 pps = 200 ms
// 15 pps = 67 ms
// 30 pps = 33 ms
const float PACKET_RATE_PPS = 15.0;
const unsigned long PACKET_INTERVAL_MS = 67;

const char* ENERGY_LOG_FILE = "/energy_log_ble.csv";

int seq = 0;
unsigned long lastSend = 0;
unsigned long lastEnergyRead = 0;
float accumulatedEnergyJ = 0.0;

bool deviceConnected = false;

class ServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* server) {
    deviceConnected = true;
    Serial.println("BLE client connected");
  }

  void onDisconnect(BLEServer* server) {
    deviceConnected = false;
    Serial.println("BLE client disconnected");
    server->startAdvertising();
  }
};

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

  BLEDevice::init("BLE_IOT_NODE_1");

  BLEServer* server = BLEDevice::createServer();
  server->setCallbacks(new ServerCallbacks());

  BLEService* service = server->createService(SERVICE_UUID);

  txCharacteristic = service->createCharacteristic(
    CHARACTERISTIC_UUID,
    BLECharacteristic::PROPERTY_NOTIFY
  );

  txCharacteristic->addDescriptor(new BLE2902());
  service->start();

  BLEAdvertising* advertising = BLEDevice::getAdvertising();
  advertising->addServiceUUID(SERVICE_UUID);
  advertising->setScanResponse(true);
  advertising->start();

  lastEnergyRead = millis();

  Serial.println("seq,tx_time_ms,current_ma,voltage_v,energy_j");
  Serial.println("BLE sender started");
}

void loop() {
  unsigned long now = millis();

  unsigned long dtMs = now - lastEnergyRead;
  if (dtMs >= 100) {
    float currentMa = ina219.getCurrent_mA();
    float voltageV = ina219.getBusVoltage_V();
    float powerW = (currentMa / 1000.0) * voltageV;

    accumulatedEnergyJ += powerW * (dtMs / 1000.0);
    lastEnergyRead = now;
  }

  if (!deviceConnected) {
    delay(100);
    return;
  }

  if (seq >= PACKET_COUNT) {
    return;
  }

  if (now - lastSend >= PACKET_INTERVAL_MS) {
    lastSend = now;

    char payload[80];

    snprintf(
      payload,
      sizeof(payload),
      "%02d,%03d,%08lu,DATA",
      NODE_ID,
      seq,
      millis()
    );

    txCharacteristic->setValue((uint8_t*)payload, strlen(payload));
    txCharacteristic->notify();

    float currentMa = ina219.getCurrent_mA();
    float voltageV = ina219.getBusVoltage_V();

    Serial.print(seq);
    Serial.print(",");
    Serial.print(millis());
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
