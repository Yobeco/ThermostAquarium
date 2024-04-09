# Code MicroPython tournant sur un Raspberry pi Pico W
# pour contrôler depuis internet le ventilateur d'un aquarium
# Actuellement le contrôle se fait par Blynk
# Essayer Grafana ?

# Version :
# 14- Enregistrement des messages d'erreurs

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
# Pour lancer un thread séparé pour vérifier la connexion
import uasyncio

#---------------------------------------------------------------------
# Gérer la boucle
from time import sleep
import time

#---------------------------------------------------------------------
# Aide la gestion des erreurs 
import sys
import io

#---------------------------------------------------------------------
# Bibliothèque Blynk
import blynklib

#---------------------------------------------------------------------
# Variables sensibles dans config.py (dans la iste .gitignore)

from config import BLYNK_KEY, WIFI_SSID_HOME, WIFI_PASSWORD_HOME, WIFI_SSID_SCHOOL, WIFI_PASSWORD_SCHOOL

#---------------------------------------------------------------------
# Connexion internet
# --> Beklin
ssid = WIFI_SSID_HOME
password = WIFI_PASSWORD_HOME
# --> École 
# ssid = WIFI_SSID_SCHOOL
# password = WIFI_PASSWORD_SCHOOL
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

wlan = None

def connect():
    
    global wlan
    #Connect to WLAN
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    while wlan.isconnected() == False:
        print('Connexion en cours...')
        connexLED.on()
        # Clear the oled display in case it has junk on it.
        oled.fill(0)
        # Afficher que la connexion est en attente
        oled.text("  En cours",10,8)
        oled.text(" de connexion",6,18)
        oled.text("  ...",30,28)
        oled.show()
        sleep(1)
        
    ip = wlan.ifconfig()[0]
    connexLED.off()
    print(f'Connecté à l\'ip : {ip}')
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    print("Adresse mac = ", mac)
    
    # Clear the oled display in case it has junk on it.
    oled.fill(0)
    # Add some text
    oled.text("Connected !",15,8)
    oled.text(ip,0,20)
    oled.text(mac,0,30)
    # Finally update the oled display so the image & text is displayed
    oled.show()
    return ip

try:
    connect()
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

# Configuration
blynk = blynklib.Blynk(BLYNK_KEY)

# Effacer l'écran avant écriture
oled.fill(0)
# Configurer le texte de confirmation la connexion à blynk
oled.text("Blynk OK !",30,50)
# Afficher
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


# Lancement d'un thread séparé pour vérifier la connexion
def connexion_thread():
    global wlan
    while True:
        if not wlan.isconnected():
            print("Tentative de reconnexion...")
            # Ajouter l'événement au fichier de log
            with open('error.log', 'a') as f:
                f.write(f'Internet interrompu\n\n')
            connexLED.on()
            connect()
        else:
            print("Connected !")
            connexLED.off()
        await uasyncio.sleep(10)  # Attendre 10 secondes avant la prochaine vérification

connexion_task = uasyncio.create_task(connexion_thread())


#---------------------------------------------------------------------
# Fonction à lancer dans la boucle principale

def main():
    
    # 1/0    # Erreur pout tester try / except
    
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
        oled.show()
                
        dataSentLED.off()
        # Attendre x ms avant la prochaine mesure
        time.sleep_ms(1000)  # Instable à 500ms

#---------------------------------------------------------------------
# Boucle principale

while True:
    
    # Essayer de lance la fonction principale
    try:
        main()
    except Exception as e:
        print(f"Une erreur est survenue : {e}")
        # Ajouter la dernière exception au fichier de log
        # Rediriger la sortie standard vers une variable "output"
        output = io.StringIO()
        # Imprimer les informations sur l'exception dans "output"
        sys.print_exception(e, output)
        with open('error.log', 'a') as f:
            f.write(output.getvalue())
            f.write(f'--------------------\n')
        time.sleep_ms(3000)         # Attendre 3s avant de recommencer main()





        
