import paho.mqtt.client as mqtt
import time
import threading
import aas_core3_rc02.types as aas_types
import aas_core3_rc02.jsonization as aas_jsonization
import json
import ast
import logging

logging.basicConfig(filename="mqtt_log.txt", level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Set up the MQTT broker and topic
MQTT_BROKER = "test.mosquitto.org"
MQTT_TOPIC = "example/topic"

global_data = None

update_event = threading.Event()
data_lock = threading.Lock()


def on_message(client, userdata, message):
    global global_data
    print("Message received via MQTT:")
    row_data = message.payload.decode('utf-8')
    print(f"Row data: {row_data}")
    print(f"Row data type: {type(row_data)}")

    try:
        # Convert the row_data from string to list
        data_list = ast.literal_eval(row_data)

        with data_lock:
            global_data = data_list
            print(f"Global data before update: {global_data}")

        update_event.set()

    except (ValueError, SyntaxError):
        print("Received message is not a valid list.")



def update_data():
    global global_data
    logger.debug("Entering update_data() function")
    while True:
        update_event.wait()

        with data_lock:
            # region AAS example

            row_data = aas_types.Property(
                value=global_data,
                value_type=aas_types.DataTypeDefXsd.STRING,
                id_short="Raw_data"
            )

            submodel_raw_data = aas_types.Submodel(
                id="urn:chiller:rawData",
                submodel_elements=[row_data]
            )
            # endregion

            # region submodel realtime operation data

            circulating_fluid_discharge_temperature = aas_types.Property(
                value=global_data[0],
                value_type=aas_types.DataTypeDefXsd.INT,
                id_short="CFDT"
            )

            circulating_fluid_discharge_pressure = aas_types.Property(
                value=global_data[2],
                value_type=aas_types.DataTypeDefXsd.INT,
                id_short="CFDP"
            )

            electric_resistivity_and_conductivity_circulating_fluid = aas_types.Property(
                value=global_data[3],
                value_type=aas_types.DataTypeDefXsd.INT,
                id_short="ERCC"
            )

            circulating_fluid_set_temperature = aas_types.Property(
                value=global_data[11],
                value_type=aas_types.DataTypeDefXsd.INT,
                id_short="CFST"
            )

            submodel_realtime_operation_data = aas_types.Submodel(
                id="urn:chiller:realtimeOperationData",
                submodel_elements=[circulating_fluid_discharge_temperature,
                                   circulating_fluid_discharge_pressure,
                                   electric_resistivity_and_conductivity_circulating_fluid,
                                   circulating_fluid_set_temperature]
            )

            asset_information = aas_types.AssetInformation(
                asset_kind=aas_types.AssetKind.TYPE
            )

            Chiller = aas_types.AssetAdministrationShell(
                id="urn:chiller",
                asset_information=asset_information,
                submodels=[
                    aas_types.Reference(
                        type=aas_types.ReferenceTypes.MODEL_REFERENCE,
                        keys=[
                            aas_types.Key(
                                type=aas_types.KeyTypes.SUBMODEL,
                                value="urn:chiller:rawData"
                            )
                        ]
                    ),
                    aas_types.Reference(
                        type=aas_types.ReferenceTypes.MODEL_REFERENCE,
                        keys=[
                            aas_types.Key(
                                type=aas_types.KeyTypes.SUBMODEL,
                                value="urn:chiller:realtimeOperationData"
                            )
                        ]
                    )
                ]
            )

            environment = aas_types.Environment(
                submodels=[submodel_raw_data,
                           submodel_realtime_operation_data]
            )

        jsonable = aas_jsonization.to_jsonable(environment)
        print(json.dumps(jsonable, indent=3))

        time.sleep(4)

        update_event.clear()


update_thread = threading.Thread(target=update_data)
update_thread.daemon = True
update_thread.start()

# Set up the MQTT client and connect to the broker
client = mqtt.Client()
client.connect(MQTT_BROKER, 1883)

# Set up the callback function to be called when a message is received
client.on_message = on_message

# Subscribe to the MQTT topic
client.subscribe(MQTT_TOPIC)

# Start the MQTT client loop to listen for incoming messages
client.loop_start()

time.sleep(3)




while True:

    time.sleep(5)



print("Done")