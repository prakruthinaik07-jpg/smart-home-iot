import network
from machine import Pin, UART
import dht
import time
import urequests
from umqtt_simple import MQTTClient

# -------- WIFI --------
SSID = "YOUR_WIFI"
PASSWORD = "YOUR PASSWORD"

BOT_TOKEN = "YOUR TELEGRAM TOKEN"
CHAT_ID = 000000 # YOUR CHAT ID FROM TELEGRAM

# -------- ADAFRUIT --------
AIO_USERNAME = "YOUR USER NAME"
AIO_KEY = "YOUR ADAFRUIT_KEY"
BROKER = "io.adafruit.com"

# -------- FEEDS (IMPORTANT: use bytes b"") --------
temp_feed = b"YOUR USER NAME/feeds/temp"
hum_feed = b"YOUR USER NAME/feeds/humidity"
light_feed = b"YOUR USER NAME/feeds/light"
smoke_feed = b"YOUR USER NAME/feeds/smoke"
fan_feed = b"YOUR USER NAME/feeds/fan"

# -------- CONNECT WIFI --------
wifi = network.WLAN(network.STA_IF)
wifi.active(True)
wifi.connect(SSID, PASSWORD)

print("Connecting WiFi...")
while not wifi.isconnected():
    time.sleep(1)

print("WiFi Connected:", wifi.ifconfig())

# -------- MQTT --------
client = MQTTClient("pico", BROKER, user=AIO_USERNAME, password=AIO_KEY)
client.connect()
print("Connected to Adafruit")

# -------- SENSORS --------
pir = Pin(1, Pin.IN)
smoke = Pin(22, Pin.IN)
ldr = Pin(21, Pin.IN)
dht_sensor = dht.DHT11(Pin(16))

# -------- OUTPUTS --------
led_pir = Pin(17, Pin.OUT)
led_temp = Pin(13, Pin.OUT)
led_ldr = Pin(18, Pin.OUT)
buzzer = Pin(10, Pin.OUT)

# -------- BLUETOOTH --------
uart = UART(1, baudrate=9600, tx=Pin(4), rx=Pin(5))

mode = "AUTO"

print("System Ready")

def send_telegram(msg):
    try:
        url = "https://api.telegram.org/bot" + BOT_TOKEN + "/sendMessage"
        
        data = {
            "chat_id": CHAT_ID,   # keep as integer here
            "text": msg
        }

        print("Sending to Telegram...")
        response = urequests.post(url, json=data)

        print("Response:", response.text)
        response.close()

        print("Sent to Telegram")

    except Exception as e:
        print("Telegram Error:", e)
        
prev_smoke = 0
prev_motion = 0
prev_temp = 0        

while True:
    try:
        # -------- BLUETOOTH CONTROL --------
        if uart.any():
            data = uart.read().decode().strip()
            print("Bluetooth:", data)
            if data == "M":
                mode = "MANUAL"
                print(" MANUAL MODE")

            elif data == "A":
                mode = "AUTO"
                print("AUTO MODE")

            # -------- MANUAL CONTROL --------
            if mode == "MANUAL":
                if data == "1":
                    led_pir.value(1)
                elif data == "0":
                    led_pir.value(0)

                elif data == "2":
                    led_temp.value(1)
                elif data == "3":
                    led_temp.value(0)

                elif data == "4":
                    led_ldr.value(1)
                elif data == "5":
                    led_ldr.value(0)

                elif data == "6":
                    buzzer.value(1)
                elif data == "7":
                    buzzer.value(0)

        # -------- READ SENSORS --------
        motion = pir.value()
        smoke_val = smoke.value()
        light_val = ldr.value()

        try:
            dht_sensor.measure()
            temp = dht_sensor.temperature()
            humidity = dht_sensor.humidity()
        except:
            temp = 0
            humidity = 0
            
        # -------- ALERT SYSTEM --------

        # Smoke Alert
        if smoke_val == 1:
            send_telegram(" ALERT! Smoke Detected")
            print("Smoke Alert Sent")

        #  Motion Alert
        if motion == 1:
            send_telegram(" Motion Detected")
            print("Motion Alert Sent")

        #  High Temperature Alert
        if temp >= 35:
            send_telegram(" High Temperature: {}°C".format(temp))
            print("Temp Alert Sent")

        # -------- UPDATE PREVIOUS VALUES --------
        prev_smoke = smoke_val
        prev_motion = motion
        prev_temp = temp    
            
        message = "Temp:{}C\nHum:{}%\nLight:{}\nSmoke:{}\nMotion:{}".format(
                temp,
                humidity,
                light_val,
                smoke_val,
                motion
        )

        send_telegram(message)
        
        if temp % 10 == 0:
            send_telegram("Status:\nTemp:{}C\nHum:{}%".format(temp, humidity))
        
        print("Sent to mobile")
        time.sleep(5)

        # -------- PRINT --------
        print("----------------------------")
        print("Mode:", mode)
        print("Temp:", temp, "°C")
        print("Humidity:", humidity, "%")
        print("Light:", light_val)
        print("Smoke:", smoke_val)
        print("Motion:", motion)
        
        # -------- SEND MESSAGE TO MOBILE --------
        msg = "Temp:{}C >>>|Hum:{}% >>>| Light:{}>>>| Smoke:{}\n".format(
            temp, humidity, light_val, smoke_val
        )

        uart.write(msg)
        print("Sent to mobile:", msg)

        # -------- AUTO MODE --------
        if mode == "AUTO":
            led_pir.value(motion)

            if temp > 33:
                led_temp.value(1)
                fan = 1
            else:
                led_temp.value(0)
                fan = 0

            led_ldr.value(light_val)

            if smoke_val == 0:
                buzzer.value(1)
            else:
                buzzer.value(0)

        # -------- SEND TO ADAFRUIT --------
        client.publish(temp_feed, str(temp))
        client.publish(hum_feed, str(humidity))
        client.publish(light_feed, str(light_val))
        client.publish(smoke_feed, str(smoke_val))
        client.publish(fan_feed, str(fan))

        print("Data sent to Adafruit")

        time.sleep(15)

    except Exception as e:
        print("Error:", e)
        time.sleep(5)