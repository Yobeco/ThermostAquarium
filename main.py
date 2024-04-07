# Code MicroPython tournant sur un Raspberry pi Pico W
# pour contrôler depuis internet le ventilateur d'un aquarium
# Actuellement le contrôle se fait par Blynk
# Essayer Grafana ?

# Affichage sur l'écran OLED I2C ssd1306 
from machine import Pin, I2C
from ssd1306 import SSD1306_I2C
import machine
import onewire, ds18x20

#---------------------------------------------------------------------
# Connexion internet
import network
import socket
from picozero import pico_temp_sensor, pico_led
# Pour afficher l'adresse mac
import ubinascii

#---------------------------------------------------------------------
# Gérer la boucle
from time import sleep
import time
#---------------------------------------------------------------------
# Bibliothèque Blynk
import blynklib

#---------------------------------------------------------------------
# Connexion internet
# --> Beklin
ssid = 'xxxxxxxxxxxxxxxxx'
password = 'xxxxxxxxxxxxxxxxxx'
# --> École 
# ssid = 'xxxxxxxxxxxxxxxxxxxxxx'
# password = 'xxxxxxxxxxxx'
#---------------------------------------------------------------------
# Allumer LED du Pico  --> Alimenté
led = machine.Pin("LED", machine.Pin.OUT)
led.on()

# Configuration de la PIN du relais
relPIN = machine.Pin(3, machine.Pin.OUT)

# Configurer et tester les LED au démarrage
connexLED = machine.Pin(10, machine.Pin.OUT)          # LED Connexion internet ROUGE
relLED = machine.Pin(13, machine.Pin.OUT)             # LED Ventilo BLEUE
dataSentLED = machine.Pin(15, machine.Pin.OUT)        # LED envoie données VERT

# Synchroniser le relai et sa LED
def relais(etat):
    relPIN.value(etat)
    relLED.value(etat)
    
connexLED.on()
relais(1)
dataSentLED.on()
time.sleep_ms(2000)
connexLED.off()
relais(0)
dataSentLED.off()

#---------------------------------------------------------------------
# OLED

# Info OLED
i2c = I2C(0, scl=Pin(9), sda=Pin(8), freq=400000)       # Initialiser I2C avec les pins GP8 & GP9 (default I2C0 s)  -->  200000 Plus instable

print("I2C Address      : "+hex(i2c.scan()[0]).upper()) # Afficher l'adresse de l'écran
print("I2C Configuration: "+str(i2c))                   # Afficher la configuration I2C

WIDTH  = 128                                            # Configuration de la largeur de l'OLED
HEIGHT = 64                                             # Configuration de la hauteur de l'OLED

oled = SSD1306_I2C(WIDTH, HEIGHT, i2c)                  # Initialisation de l'écran OLED

#---------------------------------------------------------------------
# Connection internet

def connect():
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Waiting for connection...')
        connexLED.on()
        # Clear the oled display in case it has junk on it.
        oled.fill(0)
        # Afficher que la connexion est en attente
        oled.text("   Waiting",10,8)
        oled.text("for connection",5,18)
        oled.text("  ...",30,28)
        oled.show()
        sleep(1)
    ip = wlan.ifconfig()[0]
    connexLED.off()
    print(f'Connected on {ip}')
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    print("Adresse mac = ", mac)
    
    # Clear the oled display in case it has junk on it.
    oled.fill(0)
    # Add some text
    oled.text("Connected !",12,8)
    oled.text(ip,0,20)
    oled.text(mac,0,30)
    
    # Finally update the oled display so the image & text is displayed
    oled.show()
    
    return ip

try:
    ip = connect()
except KeyboardInterrupt:
    machine.reset()
    
#---------------------------------------------------------------------
# DS18B02

ds_pin = machine.Pin(28)
 
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
 
roms = ds_sensor.scan()
 
print('Found DS devices: ', roms)

#---------------------------------------------------------------------
# Connection à Blynk

BLYNK_AUTH = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxx' #insert your Auth Token here
# base lib init
blynk = blynklib.Blynk(BLYNK_AUTH)
# Clear the oled display in case it has junk on it.
oled.fill(0)
# Add some text
oled.text("Blynk OK !",30,50)
# Finally update the oled display so the image & text is displayed
oled.show()

#---------------------------------------------------------------------
# Contrôle du seuil

tempSeuil = 0

# Ouvrir le fichier en mode lecture ('r') et lire la valeur
with open('tempMax.txt', 'r') as fichier:
    tempSeuil = float(fichier.read())  # Convertir la chaîne lue en entier

# Enregistrer un gestionnaire de pin virtuel
@blynk.on("V2")                 # virtual pin V2
# Définir une fonction pour mettre à jour la variable en fonction de la valeur du slider
def actuSeuil(valeur):
    global tempSeuil
    tempSeuil = float(valeur[0])
    with open('tempMax.txt', 'w') as fichier:
        fichier.write(str(tempSeuil))  # Convertir l'entier en chaîne pour l'écriture
        print(f"Nouveau seuil = {tempSeuil} °C")

    # envoyer_seuil_a_blynk()  # Envoyer la nouvelle valeur à Blynk

# Définir la fonction à exécuter lors de la réception de données du slider
def slider_callback(pin, value):
    actuSeuil(value)
    
# Attacher la fonction callback au pin virtuel associé au slider dans Blynk
blynk.on(2, slider_callback)

# Fonction pour envoyer la valeur de la variable à Blynk
def envoyer_seuil_a_blynk():
    blynk.virtual_write(2, tempSeuil)  # Numéro du pin virtuel pour afficher la valeur dans Blynk

#---------------------------------------------------------------------
# Contrôle du relais

# Enregistrer un gestionnaire de pin virtuel
@blynk.on("V1")                 # Briche virtuelle V1
def v1_write_handler(value):    # Lire la valeur
    if int(value[0]) == 0:
        relais(0)            # Éteindre le relais
    else:
        relais(1)            # Allumer le relais

#---------------------------------------------------------------------
# Boucle principale

while True:

    # Relancer la connexion si déconnecté ?
#     if not wlan.isconnected() :
#         connexLED.on()
#         ip = connect()
# 
#     else :
#         connexLED.off()

    ds_sensor.convert_temp()
    time.sleep_ms(750)

    for rom in roms:

        # print(rom)
        print(f"{ds_sensor.read_temp(rom)} °C / {tempSeuil} °C.")

        # Effacer l'écran pour afficher à nouveau
        oled.fill(0)
        # Afficher les informations sur l'écran
        oled.text("Temperature: ",12,8)
        temp = round(ds_sensor.read_temp(rom),1)

        oled.text(str(temp),30,30)
        oled.text("^C",75,30)
        oled.text(f"Temp max = {tempSeuil} ^C.",0,45)
        
        # Envoyer la température mesurée à Blynk
        blynk.virtual_write(0, temp)
        
        if temp >= tempSeuil :
            relais(1)
            # Changer l'état du switch et de la LED
            blynk.virtual_write(1, 1)
            blynk.virtual_write(3, 1)
        else :
            relais(0)
            # Changer l'état du switch et de la LED
            blynk.virtual_write(1, 0)
            blynk.virtual_write(3, 0)
            
        blynk.run()
        
        
        # Faire clignotter la LED à chaque mesure envoyée
        dataSentLED.on()
        time.sleep_ms(100)
        dataSentLED.off()

        # Actualiser la valeur de tempSeuil de Blynk
        envoyer_seuil_a_blynk()
        
        # Actualise l'affichage
        # oled.show()
        
        # Avec gestion des erreurs de communication I2C
        try:
            oled.show()
        except OSError as e:
            machine.reset()
                
        dataSentLED.off()
        # Attendre x ms avant la prochaine mesure
        time.sleep_ms(1000)  # Instable à 500ms



        
