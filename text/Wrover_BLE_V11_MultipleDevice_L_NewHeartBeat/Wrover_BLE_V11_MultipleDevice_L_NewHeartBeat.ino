// ============================================================================
// MULTI-SENSOR DIAGNOSTIC FIRMWARE (PHASE 1)
// Target: ESP32 Wrover + NimBLE 2.3.7
// Baud: 921600
// ============================================================================

#include <NimBLEDevice.h>
#include <WiFi.h>
#include <time.h>

#define SERIAL_BAUD 921600

// --- MULTI-NODE CONFIGURATION ---
const int NUM_NODES = 3;
const char* TARGET_NAMES[NUM_NODES] = {"L_Hip", "L_Shank", "L_Ankle"};


static NimBLEUUID serviceUUID("6E400001-B5A3-F393-E0A9-E50E24dcca9e");
static NimBLEUUID txUUID     ("6E400003-B5A3-F393-E0A9-E50E24dcca9e"); 
static NimBLEUUID rxUUID     ("6E400002-B5A3-F393-E0A9-E50E24dcca9e");

// --- WI-FI & NTP CONFIGURATION ---
#define WIFI_LED_PIN 4  
const bool USE_WIFI = true;
const char* ssid     = "LAB352";
const char* password = "032654847";
const long  gmtOffset_sec = 28800; 
const int   daylightOffset_sec = 0;
const char* ntpServer = "pool.ntp.org";

bool ntpSynced = false;
const unsigned long FAKE_EPOCH_BASE = 1740000000;

// --- DASHBOARD CONTROL ---
// Set to 'false' when streaming data to Python to prevent serial text collisions.
bool ENABLE_DASHBOARD = false;

// --- DATA STRUCTURES ---
#pragma pack(push, 1)
typedef struct {
    uint8_t  sync_1;
    uint8_t  sync_2;
    uint8_t  device_id;
    uint32_t timestamp;
    int16_t  ax, ay, az;
    int16_t  gx, gy, gz;
    int16_t  mx, my, mz;
    int16_t  q0, q1, q2, q3;
    uint8_t  checksum;
} IMU_BinaryPacket_t;
#pragma pack(pop)

struct QueueItem {
    char nodeName[16]; // ADDED: Need to know who this packet belongs to
    unsigned long esp32_timestamp; // ADDED: Unified timeline
    IMU_BinaryPacket_t packet;
};

QueueHandle_t packetQueue;

// --- SENSOR NODE STATE ---
struct DiagnosticNode {
    String name;
    bool   isConnected;
    bool   doConnect;
    bool   everStarted; 
    unsigned long discoveredAt;
    NimBLEAddress targetAddr;
    
    NimBLEClient* pClient;
    NimBLERemoteCharacteristic* pTX;
    NimBLERemoteCharacteristic* pRX;
    
    volatile bool timeSyncAcked;
    volatile bool startAcked;
    bool         systemStarted;
    
    char    asciiBuffer[64];
    uint8_t asciiIdx;
    uint8_t parseState;
    uint8_t rxBuffer[64];
    uint8_t bytesRead;
    
    unsigned long validPacketCount;
    unsigned long totalValidPackets;
    unsigned long parserSyncFailures;
    unsigned long queueOverflowCount;
    unsigned long rtcSyncTime;

    DiagnosticNode(String _name) {
        name = _name;
        isConnected = false;
        doConnect = false;
        everStarted = false;
        discoveredAt = 0; 
        targetAddr = NimBLEAddress();
        pClient = nullptr;
        pTX = nullptr;
        pRX = nullptr;
        timeSyncAcked = false;
        startAcked = false;
        systemStarted = false;
        asciiIdx = 0;
        parseState = 0;
        bytesRead = 0;
        validPacketCount = 0;
        totalValidPackets = 0;
        parserSyncFailures = 0;
        queueOverflowCount = 0;
        rtcSyncTime = 0;
        memset(asciiBuffer, 0, sizeof(asciiBuffer));
        memset(rxBuffer, 0, sizeof(rxBuffer));
    }
};

DiagnosticNode* nodes[NUM_NODES];

unsigned long getEpochTime() {
    if (ntpSynced) {
        time_t now;
        time(&now);
        return (unsigned long)now; 
    } else {
        return FAKE_EPOCH_BASE + (millis() / 1000);
    }
}

// ==========================================
// FREERTOS PROCESSING TASK (Core 1)
// ==========================================
void TaskProcessData(void *pvParameters) {
    QueueItem item;
    while (1) {
        if (xQueueReceive(packetQueue, &item, portMAX_DELAY) == pdPASS) {
            // Forward directly to terminal/Python, now using ESP32 timestamp!
            Serial.printf("%s,%lu,%lu,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n",
                item.nodeName,
                item.esp32_timestamp, // The unified time!
                item.packet.timestamp, // Original STM tick (for debugging if needed)
                item.packet.ax, item.packet.ay, item.packet.az,
                item.packet.gx, item.packet.gy, item.packet.gz,
                item.packet.mx, item.packet.my, item.packet.mz,
                item.packet.q0, item.packet.q1, item.packet.q2, item.packet.q3
            );
        }
    }
}

// ==========================================
// NIMBLE CLIENT MANIFEST CALLBACKS
// ==========================================
class ClientCallbacks : public NimBLEClientCallbacks {
    DiagnosticNode* pNode; // Class now knows WHICH node it belongs to
public:
    ClientCallbacks(DiagnosticNode* node) : pNode(node) {}

    void onDisconnect(NimBLEClient* pC, int reason) override {
        pNode->isConnected   = false;
        pNode->timeSyncAcked = false;
        pNode->startAcked    = false;
        pNode->systemStarted = false;
        pNode->bytesRead     = 0;
        pNode->asciiIdx      = 0;
        pNode->everStarted   = false; // Force fresh handshake

        Serial.printf("[BLE] Link Broken on %s (Reason: %d). Re-scanning...\n", pNode->name.c_str(), reason);
        NimBLEDevice::getScan()->start(0, false);
    }

    bool onConnParamsUpdateRequest(NimBLEClient* pC, const ble_gap_upd_params* params) override {
        return false; 
    }
};

class ScanCallbacks : public NimBLEScanCallbacks {
    void onResult(const NimBLEAdvertisedDevice* device) override {
        if (!device->haveName()) return;
        String name = String(device->getName().c_str());
        name.trim();
        
        for (int i = 0; i < NUM_NODES; i++) {
            if (name == nodes[i]->name && !nodes[i]->isConnected && !nodes[i]->doConnect) {
                nodes[i]->targetAddr = device->getAddress();
                nodes[i]->doConnect = true;
                nodes[i]->discoveredAt = millis();
                
                Serial.printf("[SCAN] Located Targeted Node: %s\n", name.c_str());
                // Notice we do NOT stop the scan here anymore! Keep looking for the others.
                break;
            }
        }
    }
};

// ==========================================
// CONNECTION HANDSHAKE ORCHESTRATION
// ==========================================
bool connectToTarget(DiagnosticNode* node) {
    Serial.printf("[CONNECT] Launching connection sequence to %s...\n", node->name.c_str());
    
    // Stop scanning briefly while we establish this specific connection
    NimBLEDevice::getScan()->stop(); 

    if (node->pClient != nullptr) {
        NimBLEDevice::deleteClient(node->pClient);
    }

    node->pClient = NimBLEDevice::createClient();
    node->pClient->setClientCallbacks(new ClientCallbacks(node), false); // Pass the node!
    node->pClient->setConnectionParams(6, 6, 0, 400, 16, 16); 
    node->pClient->setConnectTimeout(15000);

    if (!node->pClient->connect(node->targetAddr, true, false, false)) {
        Serial.printf("[CONNECT] ❌ Connection failed to %s.\n", node->name.c_str());
        return false;
    }

    delay(500);
    node->pClient->exchangeMTU();
    delay(500);
    node->pClient->discoverAttributes();

    NimBLERemoteService* pSvc = node->pClient->getService(serviceUUID);
    if (!pSvc) { node->pClient->disconnect(); return false; }

    node->pTX = pSvc->getCharacteristic(txUUID);
    node->pRX = pSvc->getCharacteristic(rxUUID);
    if (!node->pTX || !node->pRX) { node->pClient->disconnect(); return false; }

    // --- THE LAMBDA MAGIC ---
    // This inline function captures the specific 'node' pointer. 
    // It creates a dedicated pipeline for just this device.
    if (!node->pTX->subscribe(true, [node](NimBLERemoteCharacteristic* pChar, uint8_t* pData, size_t length, bool isNotify) {
        
        for (size_t i = 0; i < length; i++) {
            uint8_t b = pData[i];
            
            // MODE 1: ASCII Handshake
            if (!node->startAcked) {
                char c = (char)b;
                if (node->asciiIdx < sizeof(node->asciiBuffer) - 1) {
                    node->asciiBuffer[node->asciiIdx++] = c;
                    node->asciiBuffer[node->asciiIdx] = '\0';
                }

                if (c == '\n') {
                    if (strstr(node->asciiBuffer, "OK_T") != NULL) {
                        node->timeSyncAcked = true;
                    }
                    else if (strstr(node->asciiBuffer, "OK_S") != NULL) {
                        node->startAcked = true;
                    }
                    node->asciiIdx = 0;
                    memset(node->asciiBuffer, 0, sizeof(node->asciiBuffer));
                }
            }
            // MODE 2: Sliding Window Binary Parsing
            else {
                if (node->bytesRead < sizeof(node->rxBuffer)) {
                    node->rxBuffer[node->bytesRead++] = b;
                } else {
                    node->bytesRead = 0; // Prevent overflow
                }
                
                // Changed from >= sizeof(IMU_BinaryPacket_t) to >= 3 to allow peeking
                while (node->bytesRead >= 3) {
                    
                    // --- NEW: INTERCEPT BATTERY HEARTBEAT ---
                    if (node->rxBuffer[0] == 'B' && node->rxBuffer[1] == 'A' && node->rxBuffer[2] == 'T') {
                        int nl_idx = -1;
                        for(int j=3; j<node->bytesRead; j++) { 
                            if(node->rxBuffer[j] == '\n') { nl_idx = j; break; } 
                        }
                        
                        if (nl_idx != -1) {
                            node->rxBuffer[nl_idx] = '\0'; // Terminate string safely
                            // node->rxBuffer is now "BAT:85". atoi starting at index 4 parses the "85"
                            int bat_val = atoi((char*)&node->rxBuffer[4]); 
                            
                            // Forward to PC: "BAT,R_Hip,85\n"
                            Serial.printf("BAT,%s,%d\n", node->name.c_str(), bat_val);
                            
                            // Slide window past this ASCII message to resume binary parsing
                            int remainingBytes = node->bytesRead - (nl_idx + 1);
                            if (remainingBytes > 0) memmove(node->rxBuffer, node->rxBuffer + nl_idx + 1, remainingBytes);
                            node->bytesRead = remainingBytes;
                            continue; // Re-evaluate the while loop
                        } 
                        else if (node->bytesRead > 15) {
                            // Failsafe: if we get "BAT" but no newline ever arrives, drop 'B' and move on
                            memmove(node->rxBuffer, node->rxBuffer + 1, node->bytesRead - 1);
                            node->bytesRead--;
                            continue;
                        } else {
                            break; // Wait for more bytes to complete the BAT string
                        }
                    }

                    // --- ORIGINAL BINARY PARSER ---
                    if (node->bytesRead >= sizeof(IMU_BinaryPacket_t)) {
                        if (node->rxBuffer[0] == 0xAA && node->rxBuffer[1] == 0x55) {
                            uint8_t chk = 0;
                            for (int j = 0; j < (int)sizeof(IMU_BinaryPacket_t) - 1; j++) chk ^= node->rxBuffer[j];
                            
                            IMU_BinaryPacket_t* pkt = (IMU_BinaryPacket_t*)node->rxBuffer;
                            if (chk == pkt->checksum) {
                                node->validPacketCount++;
                                node->totalValidPackets++;
                                
                                QueueItem qItem;
                                strcpy(qItem.nodeName, node->name.c_str());
                                qItem.esp32_timestamp = millis(); 
                                qItem.packet = *pkt;
                                if (xQueueSend(packetQueue, &qItem, (TickType_t)0) != pdPASS) {
                                    node->queueOverflowCount++;
                                }
                                
                                int remainingBytes = node->bytesRead - sizeof(IMU_BinaryPacket_t);
                                if (remainingBytes > 0) memmove(node->rxBuffer, node->rxBuffer + sizeof(IMU_BinaryPacket_t), remainingBytes);
                                node->bytesRead = remainingBytes;
                            } else {
                                node->parserSyncFailures++;
                                memmove(node->rxBuffer, node->rxBuffer + 1, node->bytesRead - 1);
                                node->bytesRead--;
                            }
                        } else {
                            node->parserSyncFailures++;
                            int nextSyncIndex = -1;
                            for (int j = 1; j < node->bytesRead; j++) {
                                if (node->rxBuffer[j] == 0xAA) { nextSyncIndex = j; break; }
                            }
                            if (nextSyncIndex != -1) {
                                int remainingBytes = node->bytesRead - nextSyncIndex;
                                memmove(node->rxBuffer, node->rxBuffer + nextSyncIndex, remainingBytes);
                                node->bytesRead = remainingBytes;
                            } else {
                                node->bytesRead = 0;
                            }
                        }
                    } else {
                        break; // Wait for more bytes to complete a binary packet
                    }
                }
            }





        }
    })) {
        node->pClient->disconnect(); 
        return false;
    }

    delay(500); // Wait for the 7.5ms link to stabilize

    // 2. THE TROJAN HORSE: Shift gears to 20ms now that we are inside!
    Serial.printf("[BLE] Link established. Forcing shift to 20ms interval...\n");
    node->pClient->updateConnParams(12, 20, 0, 400);
    
    delay(800); // Give the Raytac module time to accept the new radio timing 




    // PHASE 1 HANDSHAKE
    if(node->pRX->canWrite()) {
        unsigned long now = getEpochTime();
        char timeCmd[16];
        sprintf(timeCmd, "%lu", now);
        
        int retries = 3;
        while (retries > 0 && !node->timeSyncAcked) {
            node->pRX->writeValue((uint8_t*)"T", 1, true);
            delay(10); 
            node->pRX->writeValue((uint8_t*)timeCmd, 10, true);
            unsigned long waitStart = millis();
            while(!node->timeSyncAcked && (millis() - waitStart < 10000)) delay(10);
            if (!node->timeSyncAcked) retries--;
        }
        
        if(!node->timeSyncAcked) {
            node->pClient->disconnect();
            return false;
        }
        
        node->rtcSyncTime = millis();
        node->isConnected = true;
        Serial.printf("[HANDSHAKE] ✅ Phase 1 Time Sync Completed for %s.\n", node->name.c_str());
        return true;
    }
    return false;
}

// ==========================================
// SYSTEM BOOT & LOOP ARCHITECTURE
// ==========================================
void setup() {
    Serial.begin(SERIAL_BAUD);
    delay(1000);
    Serial.println("\n=== MULTI-SENSOR STABILITY DIAGNOSTIC WINDOW ===");

    for(int i=0; i<NUM_NODES; i++) {
        nodes[i] = new DiagnosticNode(TARGET_NAMES[i]);
    }

    pinMode(WIFI_LED_PIN, OUTPUT);
    if (USE_WIFI) {
        Serial.printf("\n[WIFI] Connecting to %s...\n", ssid);
        WiFi.begin(ssid, password);
        int attempts = 0;
        while (WiFi.status() != WL_CONNECTED && attempts < 20) { delay(500); Serial.print("."); attempts++; }
        if (WiFi.status() == WL_CONNECTED) {
            digitalWrite(WIFI_LED_PIN, HIGH);
            Serial.println("\n[WIFI] Connected! Fetching NTP time...");
            configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
            struct tm timeinfo;
            int ntpAttempts = 0;
            while(!getLocalTime(&timeinfo) && ntpAttempts < 10) { delay(500); Serial.print("."); ntpAttempts++; }
            if (ntpAttempts < 10) {
                ntpSynced = true;
                Serial.println("\n[NTP] Time Synced Successfully!");
            }
        }
        WiFi.disconnect(true);
        WiFi.mode(WIFI_OFF);
        Serial.println("[WIFI] Radio powered off. Handing over to BLE...\n");
        delay(500);
    }

    // Lowered to 600 items (~31 KB of RAM). Holds 2 seconds of multi-node data.
    packetQueue = xQueueCreate(600, sizeof(QueueItem)); 
    
    if (packetQueue == NULL) {
        Serial.println("[FATAL ERROR] Failed to allocate FreeRTOS Queue in RAM!");
        while(1) { delay(100); } // Trap the system here instead of boot-looping
    }

    xTaskCreatePinnedToCore(TaskProcessData, "TaskProcessData", 8192, NULL, 2, NULL, 1);

    NimBLEDevice::init("");
    NimBLEDevice::setMTU(247);

    NimBLEScan* pScan = NimBLEDevice::getScan();
    pScan->setScanCallbacks(new ScanCallbacks());
    pScan->setActiveScan(true);
    pScan->setInterval(100);
    pScan->setWindow(99);
    pScan->start(0, false);
}

void loop() {
    bool allConnected = true;

    for (int i = 0; i < NUM_NODES; i++) {
        DiagnosticNode* n = nodes[i];

        if (!n->isConnected) {
            allConnected = false;
        }

        // Connection Execution
        if (n->doConnect && !n->isConnected) {
            if (millis() - n->discoveredAt < 8000) continue; // Wait for STM to settle
            
            n->doConnect = false;
            if (!connectToTarget(n)) {
                delay(1000);
            }
            // Resume scanning immediately after connection attempt (pass or fail)
            NimBLEDevice::getScan()->start(0, false);
        }

        // Phase 2 Handshake Execution
        if (n->isConnected && n->timeSyncAcked && !n->systemStarted) {
            if (millis() - n->rtcSyncTime >= 3000) {
                if (n->pRX != nullptr) {
                    n->pRX->writeValue((uint8_t*)"S", 1, false);
                }
                n->systemStarted = true;
                n->everStarted   = true;
            }
        }
    }

// DASHBOARD & WATCHDOG (Outputs every 3 seconds)
    static unsigned long lastDashboardTick = 0;
    if (millis() - lastDashboardTick >= 3000) { 
        unsigned long duration = millis() - lastDashboardTick;
        lastDashboardTick = millis();

        // ONLY print the table if the dashboard is enabled
        if (ENABLE_DASHBOARD) {
            Serial.println("\n==================== LIVE DATA INTEGRITY METRICS ====================");
            Serial.println("Node       | Status    | Freq (Hz) | Sync Shifts | Queue Drops | Drop %");
            Serial.println("---------------------------------------------------------------------");
        }

        for (int i = 0; i < NUM_NODES; i++) {
            DiagnosticNode* n = nodes[i];
            if (n->systemStarted && n->isConnected) {
                // Keep pinging the watchdog regardless of dashboard state
                if (n->pRX != nullptr) n->pRX->writeValue((uint8_t*)"H", 1, false);
                
                if (ENABLE_DASHBOARD) {
                    float currentHz = (n->validPacketCount * 1000.0) / duration;
                    unsigned long totalIssues = n->parserSyncFailures + n->queueOverflowCount;
                    unsigned long totalAttempted = n->totalValidPackets + totalIssues;
                    float dropRate = totalAttempted > 0 ? ((float)totalIssues / (float)totalAttempted) * 100.0 : 0.0;
                    
                    Serial.printf("%-10s | %-9s | %-9.1f | %-11lu | %-11lu | %.2f%%\n", 
                                  n->name.c_str(), "CONNECTED", currentHz, 
                                  n->parserSyncFailures, n->queueOverflowCount, dropRate);
                }
                n->validPacketCount = 0; // Reset for next window
            } else if (ENABLE_DASHBOARD) {
                Serial.printf("%-10s | %-9s | %-9.1f | %-11s | %-11s | %s\n", 
                              n->name.c_str(), "SEARCHING", 0.0, "-", "-", "-");
            }
        }
        if (ENABLE_DASHBOARD) {
            Serial.println("=====================================================================\n");
        }
    }
    
    delay(10);
}