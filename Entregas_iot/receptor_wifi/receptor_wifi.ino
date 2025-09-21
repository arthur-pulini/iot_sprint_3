#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

const char* ssid = "SUA_REDE_WIFI";
const char* password = "SUA_SENHA_WIFI";

const char* mqtt_server = "SEU_SERVIDOR_MQTT";
const int mqtt_port = 1883;
const char* mqtt_topic = "topic/mottu/networks";

WiFiClient espClient;
PubSubClient client(espClient);

String estimateDistance(int rssi) {
  if (rssi >= -50) return "0-5m (Muito perto)";
  else if (rssi >= -60) return "5-10m (Perto)";
  else if (rssi >= -70) return "10-20m (Médio)";
  else if (rssi >= -80) return "20-30m (Longe)";
  else return "30m+ (Muito longe)";
}

void setup_wifi() {
  delay(10);
  Serial.println("\nConectando a: " + String(ssid));
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi conectado! IP: " + WiFi.localIP().toString());
}

void reconnect_mqtt() {
  while (!client.connected()) {
    Serial.print("Conectando ao MQTT...");
    if (client.connect("ESP32Client")) {
      Serial.println("Conectado!");
    } else {
      Serial.println("Falha. Tentando novamente em 5s...");
      delay(5000);
    }
  }
}

void scan_and_publish_networks() {
  Serial.println("\nEscaneando redes WiFi...");
  int numNetworks = WiFi.scanNetworks();
  
  if (numNetworks == 0) {
    Serial.println("Nenhuma rede encontrada!");
    return;
  }

  DynamicJsonDocument doc(1024);
  JsonArray networks = doc.to<JsonArray>();

  for (int i = 0; i < numNetworks; i++) {
    String ssid = WiFi.SSID(i);
    if (ssid.startsWith("MOTTU_")) {
      int rssi = WiFi.RSSI(i);
      String distance = estimateDistance(rssi);

      JsonObject network = networks.createNestedObject();
      network["mac"] = WiFi.BSSIDstr(i);
      network["ssid"] = ssid;
      network["rssi"] = rssi;
      network["distance_estimate"] = distance;  // Agora é uma string descritiva

      Serial.println(
        "Rede: " + ssid + 
        " | MAC: " + WiFi.BSSIDstr(i) + 
        " | RSSI: " + String(rssi) + 
        " | Distância: " + distance
      );
    }
  }

  if (networks.size() > 0) {
    String jsonStr;
    serializeJson(doc, jsonStr);
    client.publish(mqtt_topic, jsonStr.c_str());
    Serial.println("Dados enviados ao MQTT!");
  } else {
    Serial.println("Nenhuma rede MOTTU_ encontrada.");
  }

  WiFi.scanDelete();  
}

void setup() {
  Serial.begin(115200);
  setup_wifi();
  client.setServer(mqtt_server, mqtt_port);
}

void loop() {
  if (!client.connected()) reconnect_mqtt();
  client.loop();

  scan_and_publish_networks();
  delay(30000); 
}