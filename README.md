# Projeto Quantumleap
### Integrantes
Arthur E. L. Pulini – RM: 554848

Lucas Almeida Fernandes de Moraes – RM: 557569

Victor Nascimento Cosme – RM: 558856

### Descrição do Projeto
Este repositório contém os códigos desenvolvidos para os dispositivos ESP32, utilizados em um sistema de localização indoor baseado em triangulação de sinais Wi-Fi, estes códigos estão na pasta "Entregas IOT", para mais informações sobre, acesse o link: https://youtu.be/FRIZp6bEagw.

Este projeto tem como objetivo mostrar um simulador de como seria o funcionamento do projeto em produção, simulação do esp, comunicação com o mqtt, armazenamento em banco de dados dos dados enviados pelo mqtt e dashboard no streamlit mostrando a movimentação das motos no galpão.

### Estrutura do Sistema
**Receptor**: Código referente aos ESP32 que serão posicionados nos galpões da Mottu. Esses dispositivos têm como função captar os sinais Wi-Fi emitidos pelas motos e realizar o mapeamento de suas posições por meio de triangulação.

**Roteador**: Código referente aos ESP32 que estarão instalados nas motos. Eles são responsáveis por enviar sinais Wi-Fi continuamente, permitindo que os receptores localizem os veículos.

### Requisitos de Funcionamento
É necessário ter no mínimo 3 ESP32 receptores distribuídos no galpão para garantir a triangulação precisa.

Os receptores devem estar conectados a uma rede local (LAN) para que possam enviar os dados coletados para um servidor MQTT.