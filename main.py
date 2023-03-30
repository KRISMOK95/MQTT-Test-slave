import paho.mqtt.client as mqtt
import time
# Set up the MQTT broker and topic
MQTT_BROKER = "test.mosquitto.org"
MQTT_TOPIC = "academics/IoT/data"

# Define a callback function to handle incoming messages
def on_message(client, userdata, message):
    print("Message received via MQTT:")
    print(message.payload.decode('utf-8'))

# Set up the MQTT client and connect to the broker
client = mqtt.Client()
client.connect(MQTT_BROKER, 1883)

# Set up the callback function to be called when a message is received
client.on_message = on_message

# Subscribe to the MQTT topic
client.subscribe(MQTT_TOPIC)

# Start the MQTT client loop to listen for incoming messages
client.loop_start()

while True:
    time.sleep(1)

print("Done")