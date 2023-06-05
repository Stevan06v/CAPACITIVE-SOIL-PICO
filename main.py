import dht
from machine import Pin, ADC, I2C
import time
import uasyncio
import uos
import network
import json
import gc
import urequests
import ssd1306
from microdot import Microdot, Response
from microdot_cors import CORS


# main
moisture = 0.0
humidity = 0.0
temperature = 0.0

# oled display
i2c = I2C(0, sda=Pin(16), scl=Pin(17))
display = ssd1306.SSD1306_I2C(128, 64, i2c)

displayWidth = display.width
displayHeight = display.height

# garbage collector enabled
gc.enable()

# define 
configFile = 'config.json'
calibrationFile = 'capacitive-soil-sensor-calibration.csv'
dryMoisture = 0
wetMoisture = 65535
wlan = network.WLAN(network.STA_IF)


# define wlan settings
ssid = ""
psk = ""
server = ""
port = 0

# define extras
yearBefore = "0000"
timeBefore = "00:00"
temperatureBefore = 0
humidityBefore = 0
moistureBefore = 0


print("Initializing the (dht11) sensor...")
dht11 = dht.DHT11(Pin(4))

print("Initializing the (capacitive-soil-sensor)...")
soil = ADC(Pin(26))


print("(capacitive-soil-sensor) Calibrating min/max values...")

def readConfigJson():
    global ssid,psk,server,port
    try:
        with open(configFile) as config:
            data = json.load(config)
            print(data)
    
        # dumps the json object into an element
        json_str = json.dumps(data)

        # load the json to a string
        config = json.loads(json_str)

        # init wlan-connection
        ssid = config['ssid']
        psk = config['psk']
        server = config['server']
        port = config['port']
        
        
    except Exception as err:
        print("config.json is missing ",err)

def checkIfFileExits(file):
    try:
        stat = uos.stat(file)
        print("File '{}' exists.".format(file))
        print("File size: {} bytes".format(stat[6]))
        return True
    except OSError as e:
        if e.args[0] == 2:  
            print("File '{}' does not exist.".format(file))
        else:
            print("An error occurred while checking file existence:", e)
        return False

def calculateAverage(vals):
    sum = 0 
    for iterator in vals:
        sum = sum + iterator
    return int(sum / len(vals))

def readSoilSensorValues():
    count = 1
    secs = 30
    vals = []
    while count <= secs:
        vals.append(soil.read_u16())
        print(str(secs - count) + "sec remaining...");
        count = count + 1
        time.sleep(1)
    return vals


def writeCalibrationValues(dry, wet):
    # Open the CSV file for writing
    with open(calibrationFile, 'w') as file:
        # Write the dry and wet moisture values to the file
        file.write("{},{}".format(dry, wet))

    print("capacitive-soil-sensor-calibration '{}' has been written successfully.".format(calibrationFile))


def wlanConnection(ssid, psk):
    print("-----------------------------------------------------")
    print("Validating config.json...")
    wlan.active(True)
    if psk != "" or ssid !="":
        print(ssid + ": " + psk)
        wlan.connect(ssid, psk)
        
        print(wlan.isconnected())
    else:
        print("Invalid config.json")
    print("-----------------------------------------------------")


def currentTimestampRequest():
    try:
        response = urequests.get("http://worldtimeapi.org/api/ip")
        current_time = response.json()["datetime"]
        response.close()
        return current_time
    except Exception as err:
        print("(oled) Time-api request failed...")
        raise err
        
# api time request
def getCurrentTime():
    global timeBefore
    try:
        current_time = currentTimestampRequest()
        
        time_parts = current_time.split("T")[1].split(":")[:2]  
        formatted_time = ":".join(time_parts)
        
        # safe time to display something
        timeBefore = formatted_time
        
        return formatted_time
    except Exception as err:
        return timeBefore

# convert time-response
def getCurrentYear():
    global yearBefore
    try:
        current_time = currentTimestampRequest()
        current_year = current_time[:4]
        
        yearBefore = current_year
        
        return current_year
    except Exception as err:
        return yearBefore
  
# update display
def updateCurrentYear():
    current_year = getCurrentYear()
    display.text(current_year, 0, 0)
       
def updateCurrentTime():
    current_time = getCurrentTime()
    display.text(current_time, 85, 0)



if checkIfFileExits(configFile) is True:
    print("=====================================================")
    
    # init wlan-vars
    readConfigJson()
    
    wlanConnection(ssid,psk) 
    while wlan.isconnected() == False:
        print("Trying to connect to: " + ssid + "...")
        wlanConnection(ssid, psk)
        time.sleep(3)
        
    print(wlan.ifconfig())    
    print("Successfully connected to (" + ssid + ")!")
    
    print(wlan.ifconfig())    
    
    print("=====================================================")


# calibrating the capacitive soil-sensor
if checkIfFileExits(calibrationFile) is True:
    print("=====================================================")
    print("No calibration neccessary. Reading calibrated values...")
    dry_moisture = 0
    wet_moisture = 0

    with open(calibrationFile, 'r') as file:
        lines = file.readlines()

        for line in lines:
            columns = line.strip().split(',')

            if len(columns) == 2:
                dry_moisture = int(columns[1])
                wet_moisture = int(columns[0])
                break  

    print("Dry Moisture Level:", dry_moisture)
    print("Wet Moisture Level:", wet_moisture)
    print("=====================================================")
    dryMoisture = dry_moisture
    wetMoisture = wet_moisture
    
else:
    print("Hi, you are now calibrating the sensor!")
    print("Follow the steps below to calibrate the sensor right.")
    time.sleep(5)
    
    print("=====================================================")
    print("Put the capacitive-soil-sensor in water...")
    print("=====================================================")
    
    print("Waiting 10 secounds...(then reading)");
    time.sleep(10)
    
    print("=====================================================")
    print("Now put the sensor into the water!");
    print("=====================================================")
    
    time.sleep(3)
    
    # get sensor values
    vals = readSoilSensorValues()
        
    wetMoisture = calculateAverage(vals)
    
    print("=====================================================")
    print("Dry the capacitive-soil-sensor and put it into dry soil.")
    print("=====================================================")
    
    print("Waiting 10 secounds...(then reading)");
    time.sleep(10)
    
    print("=====================================================")
    print("Now put the sensor into the dry soil!");
    print("=====================================================")
    time.sleep(3)
    
    vals = readSoilSensorValues()
    dryMoisture = calculateAverage(vals)
    
    # dryMoisture wetMoisture
    writeCalibrationValues(dryMoisture, wetMoisture)
    
    print("=====================================================")
    print("Capacitive-soil-sensor got calibrated successfully.")
    print("=====================================================")
    
    
# sensor readings
def getTemperatureValue():
    global temperatureBefore
    # temperature & humidity sensor 
    try:
        print("(dht11) measuring...")
        dht11.measure()
        temperature = dht11.temperature()
        
        # save value before current value
        temperatureBefore = temperature
        
        return temperature
    except Exception as err:
        return temperatureBefore
 
# update display  
def updateTemeperatureValue():
    global temperature
    temperature = getTemperatureValue()
    print("Temperature: {}°C".format(temperature))
    display.text("Temperature: {}C".format(temperature), 0, 20)        
    
def updateHumidityValue():
    global humidity
    humidity = getHumidityValue()
    print("Humidty: {}%".format(humidity))
    display.text("Humidty: {}%".format(humidity), 0, 35)

def updateMoistureValue():
    global moisture
    moisture = getMoistureValue()
    print("Moisture: {}%".format(mositure))
    display.text("Moisture: {}%".format(mositure), 0, 50)
    
    
    
def getAllSensorValues():
    
    dht11.measure()
    
    humidity = dht11.humidity()
    temperature = dht11.temperature()
    
    data = {
        "temperature": temperature,
        "humidity": humidity,
        "moisture": getMoistureValue()
    }
    
    dataString = json.dumps(data)
    print(dataString)
    
    return dataString
    


# Setup web server
app = Microdot()

cors = CORS(app, allowed_origins=['http://localhost'], handle_cors=True, allowed_methods=['GET', 'POST'])

def add_cors_headers(request, response):
    origin = request.headers.get('Origin')
    if origin in ['http://localhost']:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST'
        response.headers['Access-Control-Allow-Headers'] = '*'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers['Access-Control-Max-Age'] = '3600'


@app.route('/plantify')
def hello(request):
    response = Response(getAllSensorValues())
    add_cors_headers(request, response)
    
    return response




def start_server():
    print('Starting microdot app')
    try:
        app.run(port=80)
    except:
        app.shutdown()
        
start_server()  

# main loop
while True:
    # clear the display
    display.fill(0)
    
    # update time
    updateCurrentYear()
    updateCurrentTime()
    
    display.hline(0, 10, displayWidth - 1, 1)
    
    # update dht11-values
    updateTemeperatureValue()
    time.sleep(1)
    updateHumidityValue()
    
    # update moisture values
    updateMoistureValue()
    
    display.show()
    time.sleep(3)
