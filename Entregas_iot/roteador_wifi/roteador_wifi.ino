#include <WiFi.h>

// Defina um identificador único para cada moto (ex: ID da moto ou número de série)
#define MOTO_ID "MOTTU_123"

// Tempo de espera antes de entrar em deep sleep (em milissegundos)
#define TEMPO_ATIVO_MS 10000 // 10 segundos

// Tempo em que o ESP ficará dormindo (em microssegundos)
#define TEMPO_SLEEP_US (3600 * 1000000ULL) // 1 hora

void setup() {
  Serial.begin(115200);
  delay(100);

  Serial.println("Inicializando modo Access Point...");

  // Inicia o Wi-Fi em modo Access Point com SSID fixo
  WiFi.mode(WIFI_AP);
  WiFi.softAP(MOTO_ID);

  Serial.print("Access Point ativo com nome: ");
  Serial.println(MOTO_ID);

  // Aguarda alguns segundos antes de entrar em modo de baixo consumo
  delay(TEMPO_ATIVO_MS);

  Serial.println("Entrando em deep sleep por 1 hora...");
  esp_deep_sleep(TEMPO_SLEEP_US); // Entra em modo de sono profundo
}

void loop() {
  // Nada aqui, pois o loop nunca será executado (só o setup roda antes do deep sleep)
}
