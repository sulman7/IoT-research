#include <SPI.h>
#include <LoRa.h>
#include <Wire.h>
#include <Adafruit_INA219.h>
#include <SD.h>
#include <SPI.h>

#define SD_CS 13
#define LORA_SS   5
#define LORA_RST  14
#define LORA_DIO0 2

Adafruit_INA219 ina219;

//keiciam pagal scenariju
const int NODE_ID = 1;
const int TRIAL_ID = 1;
const int PACKET_COUNT = 60;

// 0.1 pps = 10000 ms
// 0.5 pps = 2000 ms
// 1.0 pps = 1000 ms
const float PACKET_RATE_PPS = 1.0;
const unsigned long PACKET_INTERVAL_MS = 1000;

const char* ENERGY_LOG_FILE = "/energy_log_lora.csv";

int seq = 0;
unsigned long lastSend = 0;
unsigned long lastEnergyRead = 0;
float accumulatedEnergyJ = 0.0;

void setup() {
  Serial.begin(115200);
  delay(1000);

  if (!ina219.begin()) {
    Serial.println("INA219 not found");
    while (true);
  }

  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(868E6)) {
    Serial.println("LoRa init failed");
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

  LoRa.setTxPower(14);
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);

  lastEnergyRead = millis();

  Serial.println("seq,tx_time_ms,current_ma,voltage_v,energy_j");
  Serial.println("LoRa sender started");
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

    LoRa.beginPacket();
    LoRa.print(payload);
    LoRa.endPacket();

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
