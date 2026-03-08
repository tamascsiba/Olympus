#include <PN532_HSU.h>
#include <PN532.h>
#include <HardwareSerial.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

/*
===============================================================
ESP32-S3 NFC Access Control System
---------------------------------------------------------------
Description:
This firmware runs on an ESP32-S3 and controls a gate using
two PN532 NFC readers.

Workflow:
1. NFC card is scanned by Reader 1 or Reader 2
2. UID of the card is sent to a backend server via HTTP POST
3. The server checks if the card is authorized
4. If authorized, the server responds with "GATE_OPEN"
5. ESP32 activates a relay to open the gate

Additional Features:
- Dual PN532 readers
- WiFi auto-reconnect
- HTTP request protection
- Card re-read cooldown
- Gate state machine
===============================================================
*/

// WiFi credentials
const char* ssid = "wifi_ssid";
const char* password = "wifi_password";

// Hardware serial ports for PN532 modules
HardwareSerial mySerial1(1);
HardwareSerial mySerial2(2);

// NFC reader instances
PN532_HSU pn532hsu1(mySerial1);
PN532 nfc1(pn532hsu1);

PN532_HSU pn532hsu2(mySerial2);
PN532 nfc2(pn532hsu2);

// Gate control (relay or LED)
const int gatePin = 10;
bool gateOpen = false;
unsigned long gateOpenStart = 0;
const unsigned long gateOpenDuration = 3000; // gate stays open for 3 seconds

// HTTP request state control
bool httpInProgress = false;
unsigned long httpTimeout = 3000; // request timeout

// WiFi reconnect timer
unsigned long lastWiFiCheck = 0;
const unsigned long wifiCheckInterval = 10000; // check every 10 seconds

// Prevent multiple reads of the same card
uint8_t lastUID1[7];
uint8_t lastUIDLength1 = 0;
unsigned long lastReadTime1 = 0;

uint8_t lastUID2[7];
uint8_t lastUIDLength2 = 0;
unsigned long lastReadTime2 = 0;

const unsigned long cardCooldown = 2000; // cooldown between reads

// Card release state
bool needsRelease1 = false;
bool needsRelease2 = false;


/*
===============================================================
Helper Functions
===============================================================
*/

// Print UID to Serial Monitor
void printUID(uint8_t *uid, uint8_t uidLength) {
  for (uint8_t i = 0; i < uidLength; i++) {
    if (uid[i] < 0x10) Serial.print("0");
    Serial.print(uid[i], HEX);
    if (i < uidLength - 1) Serial.print(":");
  }
  Serial.println();
}

// Compare two card UIDs
bool compareUID(uint8_t *uid1, uint8_t *uid2, uint8_t len1, uint8_t len2) {
  if (len1 != len2) return false;

  for (uint8_t i = 0; i < len1; i++) {
    if (uid1[i] != uid2[i]) return false;
  }

  return true;
}

// Connect to WiFi network
void connectWiFi() {
  Serial.println("\nConnecting to WiFi...");
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
}

// Periodically check WiFi connection
void checkWiFi() {

  unsigned long currentMillis = millis();

  if (currentMillis - lastWiFiCheck >= wifiCheckInterval) {

    lastWiFiCheck = currentMillis;

    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("⚠ WiFi connection lost! Reconnecting...");
      connectWiFi();
    }
    else {
      Serial.println("✓ WiFi OK (RSSI: " + String(WiFi.RSSI()) + " dBm)");
    }

  }
}


/*
===============================================================
Gate Control State Machine
===============================================================
*/

// Activate relay to open the gate
void openGate() {

  digitalWrite(gatePin, HIGH);
  gateOpen = true;
  gateOpenStart = millis();

  Serial.println(">>> Gate OPEN");

}

// Automatically close gate after timeout
void updateGate() {

  if (gateOpen && (millis() - gateOpenStart >= gateOpenDuration)) {

    digitalWrite(gatePin, LOW);
    gateOpen = false;

    Serial.println(">>> Gate CLOSED");

  }

}


/*
===============================================================
Server Communication
===============================================================
*/

// Send scanned card UID to backend server
void sendToServer(uint8_t *uid, uint8_t uidLength, uint8_t readerNum) {

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠ No WiFi connection, request skipped!");
    return;
  }

  if (httpInProgress) {
    Serial.println("⚠ HTTP request already in progress!");
    return;
  }

  httpInProgress = true;

  // Convert UID to HEX string
  String uidStr = "";

  for (uint8_t i = 0; i < uidLength; i++) {

    if (uid[i] < 0x10) uidStr += "0";
    uidStr += String(uid[i], HEX);

    if (i < uidLength - 1) uidStr += ":";

  }

  uidStr.toUpperCase();

  // Create JSON body
  String postData = "{\"reader\": " + String(readerNum) + ", \"uid\": \"" + uidStr + "\"}";

  WiFiClient client;
  HTTPClient http;

  String serverUrl = "http://IP_address/api/check_card/";

  Serial.print("[Reader");
  Serial.print(readerNum);
  Serial.print("] POST -> ");
  Serial.println(serverUrl);

  http.setTimeout(httpTimeout);

  if (!http.begin(client, serverUrl)) {

    Serial.println("✗ HTTP begin failed!");

    http.end();
    httpInProgress = false;

    return;

  }

  http.addHeader("Content-Type", "application/json");

  int httpResponseCode = http.POST(postData);

  if (httpResponseCode > 0) {

    Serial.print("✓ HTTP ");
    Serial.println(httpResponseCode);

    String resp = http.getString();

    Serial.print("Server response: ");
    Serial.println(resp);

    StaticJsonDocument<200> doc;

    DeserializationError error = deserializeJson(doc, resp.c_str());

    resp = "";  // free memory buffer

    if (!error) {

      const char* action = doc["action"];

      if (action && String(action) == "GATE_OPEN") {

        Serial.println(">> GATE_OPEN - Opening gate");
        openGate();

      }
      else {

        Serial.println(">> Access DENIED");

      }

    }
    else {

      Serial.println("✗ JSON parsing error!");

    }

  }
  else {

    Serial.print("✗ POST error: ");
    Serial.println(httpResponseCode);

  }

  http.end();

  // Mark card for release
  if (readerNum == 1) needsRelease1 = true;
  else needsRelease2 = true;

  httpInProgress = false;

  delay(50);  // allow LWIP cleanup

}


/*
===============================================================
Card Release
===============================================================
*/

// Release NFC cards after reading
void releaseCards() {

  if (needsRelease1) {

    nfc1.inRelease();
    needsRelease1 = false;

    Serial.println("[Reader1] Card released");

  }

  if (needsRelease2) {

    nfc2.inRelease();
    needsRelease2 = false;

    Serial.println("[Reader2] Card released");

  }

}


/*
===============================================================
Setup
===============================================================
*/

void setup() {

  Serial.begin(115200);
  while (!Serial);

  Serial.println("\n=== ESP32-S3 NFC Reader + WiFi (Stable Version) ===\n");

  pinMode(gatePin, OUTPUT);
  digitalWrite(gatePin, LOW);

  connectWiFi();

  Serial.println("\n--- Initializing PN532 modules ---");

  // Serial configuration for PN532 readers
  mySerial1.begin(115200, SERIAL_8N1, 5, 8);
  mySerial2.begin(115200, SERIAL_8N1, 4, 9);

  nfc1.begin();

  if (!nfc1.getFirmwareVersion()) {

    Serial.println("✗ PN532 #1 not found!");
    while (1);

  }

  Serial.println("✓ PN532 #1 OK");
  nfc1.SAMConfig();

  nfc2.begin();

  if (!nfc2.getFirmwareVersion()) {

    Serial.println("✗ PN532 #2 not found!");
    while (1);

  }

  Serial.println("✓ PN532 #2 OK");
  nfc2.SAMConfig();

  Serial.println("\n=== System Ready ===\n");

}


/*
===============================================================
Main Loop
===============================================================
*/

void loop() {

  checkWiFi();
  updateGate();
  releaseCards();

  unsigned long now = millis();


  // Reader 1
  if (now - lastReadTime1 >= cardCooldown) {

    uint8_t uid1[7];
    uint8_t uidLen1;

    if (nfc1.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid1, &uidLen1, 100)) {

      if (!compareUID(uid1, lastUID1, uidLen1, lastUIDLength1)) {

        memcpy(lastUID1, uid1, uidLen1);

        lastUIDLength1 = uidLen1;
        lastReadTime1 = now;

        sendToServer(uid1, uidLen1, 1);

      }
      else {

        nfc1.inRelease();

      }

    }
    else {

      if (now - lastReadTime1 >= cardCooldown * 2) {
        lastUIDLength1 = 0;
      }

    }

  }


  // Reader 2
  if (now - lastReadTime2 >= cardCooldown) {

    uint8_t uid2[7];
    uint8_t uidLen2;

    if (nfc2.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid2, &uidLen2, 100)) {

      if (!compareUID(uid2, lastUID2, uidLen2, lastUIDLength2)) {

        memcpy(lastUID2, uid2, uidLen2);

        lastUIDLength2 = uidLen2;
        lastReadTime2 = now;

        sendToServer(uid2, uidLen2, 2);

      }
      else {

        nfc2.inRelease();

      }

    }
    else {

      if (now - lastReadTime2 >= cardCooldown * 2) {
        lastUIDLength2 = 0;
      }

    }

  }

  delay(5);

}