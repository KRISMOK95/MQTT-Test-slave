import paho.mqtt.client as mqtt
import time
import threading
import aas_core3_rc02.types as aas_types
import aas_core3_rc02.jsonization as aas_jsonization
import json
import ast
import logging.handlers
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import requests


#region logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# create a file handler
log_file = 'mqtt_log.txt'
max_log_size = 1024 * 1024 * 10  # 10 MB
backup_count = 1
handler = logging.handlers.RotatingFileHandler(log_file, maxBytes=max_log_size, backupCount=backup_count)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

#endregion

#region Set up the MQTT broker and topic
MQTT_BROKER = "test.mosquitto.org"
MQTT_TOPIC = "example/topic"

global_data = None
global_data_pre = None
last_log_time = 0
update_event = threading.Event()
data_lock = threading.Lock()
#endregion

#region FastAPI

global_jsonable = None
app = FastAPI()

class EnvironmentData(BaseModel):
    submodels: list

@app.get("/data", response_model=EnvironmentData)
def get_data():
    global data_lock, global_jsonable
    with data_lock:
        if global_jsonable is not None:
            return JSONResponse(content=global_jsonable)
        else:
            raise HTTPException(status_code=404, detail="Data not available")


class StandardData(BaseModel):
    submodels: list
@app.get("/standardData", response_model=StandardData)
def get_data():
    global global_data_pre
    if global_data_pre is not None:
        return JSONResponse(content=global_data_pre)
    else:
        raise HTTPException(status_code=404, detail="Data not available")

#endregion

#region set initial values

def set_initial_values():
    global global_data_pre

    submodel_chiller_identification = aas_types.Submodel(
        id="urn:zhaw:ims:chiller:543fsfds99342:identification",
        submodel_elements=[
            aas_types.Property(
                value="Thermo-chiller",
                id_short="name",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="Circulating Fluid Temperature Controller Thermo chiller",
                id_short="full_name",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="yX488",
                id_short="serial_no",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="HRS050-AF-20",
                id_short="model",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="HRS",
                id_short="series",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="69",
                id_short="weight_kg",
                value_type=aas_types.DataTypeDefXsd.INT
            ),
            aas_types.Property(
                value="976x377x592",
                id_short="size_mm",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="SMC (Japan)",
                id_short="manufacturer",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="HRX-OM-0020 HRX-OM-0021",
                id_short="manual",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
        ]
    )

    submodel_chiller_standard_technical_data = aas_types.Submodel(
        id="urn:zhaw:ims:chiller:543fsfds99342:standard_technical_data",
        submodel_elements=[
            aas_types.Property(
                value="2.5",
                id_short="capacity_aic_ka",
                value_type=aas_types.DataTypeDefXsd.FLOAT
            ),
            aas_types.Property(
                value="30-70",
                id_short="humidity_range_percent",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),  # AAS.TYPES.Range should replace this property
            aas_types.Property(
                value="3000",
                id_short="altitude_m",
                value_type=aas_types.DataTypeDefXsd.INT
            ),
            aas_types.Property(
                value="R410A (HFC)",
                id_short="refrigerant",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),  # Could link to another URL or website (aas_types.DataTypeDefXsd.AnyURI)
            aas_types.Property(
                value="0.65",
                id_short="refrigerant_charge_kg",
                value_type=aas_types.DataTypeDefXsd.FLOAT
            ),
            aas_types.Property(
                value="PID control",
                id_short="control_method",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="65/68",
                id_short="noise_level_50Hz_60Hz_dB",
                value_type=aas_types.DataTypeDefXsd.STRING
            )
        ]
    )

    submodel_chiller_standard_circulating_fluid_system_data = aas_types.Submodel(
        id="urn:zhaw:ims:chiller:543fsfds99342:standard_circulating_fluid_system_data",
        submodel_elements=[
            aas_types.Property(
                value="Tap water",
                id_short="circulating_fluid",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="5-40",
                id_short="set_temperature_range_celsius",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="4700/5100",
                id_short="cooling_capacity_50Hz_60Hz_watt",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),  # Separate 50 / 60 Hz and convert string -> int
            aas_types.Property(
                value="1100/1400",
                id_short="heating_capacity_50Hz_60Hz_watt",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),  # The unit can be outside (remind Markco)
            aas_types.Property(
                value="0.1",
                id_short="temperature_stability",
                value_type=aas_types.DataTypeDefXsd.FLOAT
            ),
            aas_types.Property(
                value="23 (0.24 MPa)/28 (0.32 MPa)",
                id_short="pump_rated_flow_50Hz_60Hz_lmin",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="31/42",
                id_short="pump_max_flow_rate_50Hz_60Hz_lmin",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="50",
                id_short="pump_max_head_50Hz_60Hz_m",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="550",
                id_short="pump_output_W",
                value_type=aas_types.DataTypeDefXsd.FLOAT
            ),
            aas_types.Property(
                value="5",
                id_short="tank_capacity_L",
                value_type=aas_types.DataTypeDefXsd.FLOAT
            ),
            aas_types.Property(
                value="RC1/2",
                id_short="port_size",
                value_type=aas_types.DataTypeDefXsd.STRING
            )
        ]
    )

    submodel_chiller_standard_electrical_system_data = aas_types.Submodel(
        id="urn:zhaw:ims:chiller:543fsfds99342:standard_electrical_system_data",
        submodel_elements=[
            aas_types.Property(
                value="200-230",
                id_short="power_supply_50Hz_60Hz_vac",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="20",
                id_short="circuit_protector_a",
                value_type=aas_types.DataTypeDefXsd.FLOAT
            ),
            aas_types.Property(
                value="20",
                id_short="applicable_earth_leakage_breaker_capacity_a",
                value_type=aas_types.DataTypeDefXsd.FLOAT
            ),
            aas_types.Property(
                value="8/11",
                id_short="rated_operating_current_a",
                value_type=aas_types.DataTypeDefXsd.STRING
            ),
            aas_types.Property(
                value="1.7/2.2",
                id_short="rated_power_consumption_50Hz_60Hz_kva",
                value_type=aas_types.DataTypeDefXsd.STRING
            )
        ]
    )

    asset_information = aas_types.AssetInformation(
        asset_kind=aas_types.AssetKind.TYPE
    )

    chiller = aas_types.AssetAdministrationShell(
        id="urn:zhaw:ims:chiller:543fsfds99342",
        asset_information=asset_information,
        submodels=[
            aas_types.Reference(
                type=aas_types.ReferenceTypes.MODEL_REFERENCE,
                keys=[
                    aas_types.Key(
                        type=aas_types.KeyTypes.SUBMODEL,
                        value="urn:zhaw:ims:chiller:543fsfds99342:identification"
                    )
                ]
            ),
            aas_types.Reference(
                type=aas_types.ReferenceTypes.MODEL_REFERENCE,
                keys=[
                    aas_types.Key(
                        type=aas_types.KeyTypes.SUBMODEL,
                        value="urn:zhaw:ims:chiller:543fsfds99342:standard_technical_data"
                    )
                ]
            ),
            aas_types.Reference(
                type=aas_types.ReferenceTypes.MODEL_REFERENCE,
                keys=[
                    aas_types.Key(
                        type=aas_types.KeyTypes.SUBMODEL,
                        value="urn:zhaw:ims:chiller:543fsfds99342:standard_circulating_fluid_system_data"
                    )
                ]
            ),
            aas_types.Reference(
                type=aas_types.ReferenceTypes.MODEL_REFERENCE,
                keys=[
                    aas_types.Key(
                        type=aas_types.KeyTypes.SUBMODEL,
                        value="urn:zhaw:ims:chiller:543fsfds99342:standard_electrical_system_data"
                    )
                ]
            )
        ]
    )

    environment = aas_types.Environment(
        submodels=[
                   submodel_chiller_identification,
                   submodel_chiller_standard_technical_data,
                   submodel_chiller_standard_circulating_fluid_system_data,
                   submodel_chiller_standard_electrical_system_data
                   ]
    )

    jsonable_pre = aas_jsonization.to_jsonable(environment)

    global_data_pre = jsonable_pre


#endregion

#region on_message()
def on_message(client, userdata, message):
    global global_data
    global last_log_time
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
        if time.time() - last_log_time >= 30:
            logger.debug(f"Row data: {row_data}")
            last_log_time = time.time()

        update_event.set()

    except (ValueError, SyntaxError):
        print("Received message is not a valid list.")

#endregion

def update_data():
    global global_data, global_jsonable

    logger.debug("Entering update_data() function")

    set_initial_values()

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
                id_short="CFDT",
                semantic_id=aas_types.Reference(
                    type=aas_types.ReferenceTypes.MODEL_REFERENCE,
                    keys=[
                        aas_types.Key(
                            type=aas_types.KeyTypes.CONCEPT_DESCRIPTION,
                            value="urn:zhaw:conceptDescription:circulating_fluid_discharge_temperature"
                        )
                    ]
                )
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
                           submodel_realtime_operation_data
                           ],
                concept_descriptions=[
                    aas_types.ConceptDescription(
                        id="urn:zhaw:conceptDescription:circulating_fluid_discharge_temperature",
                        embedded_data_specifications=[
                            aas_types.EmbeddedDataSpecification(
                                data_specification=aas_types.Reference(
                                    type=aas_types.ReferenceTypes.GLOBAL_REFERENCE,
                                    keys=[
                                        aas_types.Key(
                                            type=aas_types.KeyTypes.GLOBAL_REFERENCE,
                                            value="0112/2///61360_4#AAA621"
                                        )
                                    ]
                                ),
                                data_specification_content=aas_types.DataSpecificationIEC61360(
                                    preferred_name=[
                                        aas_types.LangString(
                                            language="en",
                                            text="temperature"
                                        )
                                    ],
                                    short_name=[
                                        aas_types.LangString(
                                            language="en",
                                            text=""
                                        )
                                    ],
                                    definition=[
                                        aas_types.LangString(
                                            language="en",
                                            text="Circulating fluid discharge temperature is the temperature of the fluid leaving the system for circulation"
                                        )
                                    ],
                                    unit="°C"
                                )
                            )
                        ]
                    )
                ]
            )

            jsonable = aas_jsonization.to_jsonable(environment)
            global_jsonable = jsonable
        print(jsonable)
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

if __name__ == "__main__":

    uvicorn.run(app, host="0.0.0.0", port=8000)


while True:
    logger.debug('Logging every 30 seconds')
    time.sleep(30)



print("Done")