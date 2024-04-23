# Code MicroPython tournant sur un Raspberry pi Pico W
# pour contrôler depuis internet le ventilateur d'un aquarium
# Actuellement le contrôle se fait par Blynk
# Essayer Grafana ?

# Version :
# 17- Reconnexion à internet en cas de coupure - 3

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
# Vérifier Connexion internet sur autre Thread
import _thread

#---------------------------------------------------------------------
# Gérer les boucles
import time

#---------------------------------------------------------------------
# Aide la gestion des erreurs 
import sys
import io

#---------------------------------------------------------------------
# Bibliothèque Blynk
import blynklib

#---------------------------------------------------------------------
# Variables sensibles dans config.py (qui est dans la liste .gitignore)

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

# Fonction unique pour contrôler le relai et sa LED
def relais(etat):
    relPIN.value(etat)
    relLED.value(etat)
    
connexLED.on()
relais(1)
dataSentLED.on()
time.sleep(2)          # Laisser les LED allumée 2s
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

# Création d'un objet global pour le module WLAN
wlan = None

def connect():

    global wlan
    
    message = 'Connexion en cours...'

    wlan = network.WLAN(network.STA_IF)     # Crée une instance de l’interface Wi-Fi en mode station.
    wlan.active(True)                       # Activation de l'interface WLAN
    
    wlan.connect(ssid, password)
    
    a = 0      # Compteur de tentatives de connexions au Wifi
    
    while wlan.isconnected() == False:
        a = a + 1
        print(message)
        print(f"Essai n°{a}")
        connexLED.on()
        # Effacer l'OLED
        oled.fill(0)
        # Afficher que la connexion est en attente
        oled.text("   Connexion",0,7)
        oled.text("    en cours", 0,20)
        oled.text("      ...",0,30)
        oled.text(f"   Essai n^{a}",0,45)    # Afficher le numéro d'essai
        oled.show()
        
        if a >= 5:
            machine.reset()
        
        time.sleep(a * 10)       # Attendre 10s, puis 20s... si la connexion n'a pas réussi
        # Redémarrage du Pico si pas de connexion internet au bout de 2 min 30 (10 + 20 + 30 + 40 + 50s) ?
        
    ip = wlan.ifconfig()[0]
    connexLED.off()
    print(f'Connecté à l\'ip : {ip}')
    mac = ubinascii.hexlify(network.WLAN().config('mac'),':').decode()
    print("Adresse mac = ", mac)
    
    # Affichage des infos sur l'OLED
    oled.fill(0)
    oled.text("Connected !",15,8)
    oled.text(ip,0,20)
    oled.text(mac,0,30)
    oled.show()
    return ip

    # Essayer de lance la fonction de connexion à internet
try:
    connect()
    
except Exception as e:
    
    connexLED.off()
    
    print(f"--> Erreur de connexion à internet : {e}")
    # Ajouter la dernière exception au fichier de log
    # Rediriger la sortie standard vers une variable "output"
    output = io.StringIO()
    # Imprimer les informations sur l'exception dans "output"
    sys.print_exception(e, output)
    with open('error.log', 'a') as f:
        f.write(f"--> Erreur de connexion à internet : {e}\n")
        f.write(output.getvalue())
        f.write(f'--------------------\n')
    
    # Affichage des infos sur l'OLED
    oled.fill(0)
    oled.text(" Non connecte",0,8)
    oled.text("    au Wifi",0,25)
    oled.text("Reinitialisation",0,35)
    oled.text("  dans 2 min",0,50)
    oled.show()
    
    # Redémarrage du Pico après une pause
    time.sleep(120)         # Attendre 120s
    machine.reset()
    
#---------------------------------------------------------------------
# DS18B02

ds_pin = machine.Pin(28)
 
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))
 
roms = ds_sensor.scan()
 
print('Found DS devices: ', roms)

#---------------------------------------------------------------------
# Connection à Blynk

# Essayer de lancer la connexion à Blynk
try: 
    blynk = blynklib.Blynk(BLYNK_KEY)
    
except Exception as e:
    
    for _ in range(10):
        connexLED.on()
        time.sleep(0.1)
        connexLED.off()
        time.sleep(0.1)
    
    connexLED.on()
    
    print(f"--> Erreur de connexion à Blynk : {e}")
    # Ajouter la dernière exception au fichier de log
    # Rediriger la sortie standard vers une variable "output"
    output = io.StringIO()
    # Imprimer les informations sur l'exception dans "output"
    sys.print_exception(e, output)
    with open('error.log', 'a') as f:
        f.write(f"--> Erreur de connexion à Blynk : {e}\n")
        f.write(output.getvalue())
        f.write(f'--------------------\n')
        
    # Affichage des infos sur l'OLED
    oled.fill(0)
    oled.text("  Non connecte",0,8)
    oled.text("    a Blynk",0,20)
    oled.text("Reinitialisation",0,35)
    oled.text("   dans 2 min",0,50)
    oled.show()
    
    time.sleep(120)         # Attendre 120s avant de redémarrer
    machine.reset()

connexLED.off()
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
# Réinitialisation du Pico si wifi coupé --> pas moyen de RElancer connect()...
def connexion_thread():
    global wlan
    while True:
        if not wlan.isconnected():
            print("Internet interrompu !")
            # Ajouter l'événement au fichier de log
            with open('error.log', 'a') as f:
                f.write(f'Internet interrompu !\n\n')
                
            connexLED.on()
            
            oled.fill(0)
            oled.text("  Pas de Wifi",0,8)
            oled.text("Reinitialisation",0,20)
            oled.text("pour reconnexion",0,35)
            oled.text("   dans 2 min",0,50)
            oled.show()
            time.sleep(120)          # Attendre 2 min avant reset
            machine.reset()
        else:
            print("Connexion ok !")
            connexLED.off()
        
        time.sleep(120) # Attendre 120 secondes avant la prochaine vérification

# Lancer connexion_thread() sur un second Thread
second_thread = _thread.start_new_thread(connexion_thread, ())


#---------------------------------------------------------------------
# Fonction à lancer dans la boucle principale

def main():
    # 1/0    # Erreur pout tester try / except
    
    # Instancier l'objet "ds_sensor" de réception des données du DS1820
    ds_sensor.convert_temp()
    
    time.sleep(1)     # Laisser 1s pour que la connexion se fasse

    for rom in roms:

        print(f"{ds_sensor.read_temp(rom)} °C / {tempSeuil} °C.")

        # Effacer l'écran pour afficher à nouveau
        oled.fill(0)
        # Afficher les informations sur l'écran
        oled.text("Temperature: ",12,8)
        temp = round(ds_sensor.read_temp(rom),1)

        oled.text(str(temp),30,30)
        oled.text("^C",75,30)
        oled.text(f"Temp max = {tempSeuil} ^C.",0,45)
        
        # Si la connexion est établie --> envoyer la température mesurée à Blynk
        if wlan.isconnected():        # Éviter les messages d'erreurs en cas de déconnexion internet
            try:
                blynk.virtual_write(0, temp)
            except Exception as e:
                print(f"--> Erreur de connexion à Blynk : {e}")
        
        # Mettre un PID !!!
        if temp >= tempSeuil :
            # Activer le relais
            relais(1)
            
            # Actualiser l'état du switch et de la LED sur Blynk
            # seulement si la connexion est établie
            if wlan.isconnected():
                try:
                    blynk.virtual_write(1, 1)
                    blynk.virtual_write(3, 1)
                except Exception as e:
                    print(f"--> Erreur de connexion à Blynk : {e}")
        else :
            # Éteindre le relais
            relais(0)
            
            # Actualiser l'état du switch et de la LED sur Blynk
            # seulement si la connexion est établie
            if wlan.isconnected():
                try :
                    blynk.virtual_write(1, 0)
                    blynk.virtual_write(3, 0)
                except Exception as e:
                    print(f"--> Erreur de connexion à Blynk : {e}")
        
        # Envoyer les infos à Blynk
        # seulement si la connexion est établie
        if wlan.isconnected():
            try:
                blynk.run()
            except Exception as e:
                print(f"--> Erreur de connexion à Blynk : {e}")
        
        # Faire clignotter la LED à chaque mesure envoyée
        # si la connexion est établie
        if wlan.isconnected():
            connexLED.off()
            
            dataSentLED.on()
            time.sleep_ms(300)
            dataSentLED.off()
        else :                     # Si non connecté : clignoter
            connexLED.on()
            
            for _ in range(4):
                dataSentLED.on()
                time.sleep_ms(50)
                dataSentLED.off()
                time.sleep_ms(50)

        # Actualiser la valeur de tempSeuil de Blynk
        # seulement si la connexion est établie
        if wlan.isconnected():
            try:
                envoyer_seuil_a_blynk()
            except Exception as e:
                print(f"--> Erreur de connexion à Blynk : {e}")
                
        # Actualise l'affichage de l'OLED
        oled.show()
                
        # Attendre x ms avant la prochaine mesure
        time.sleep(5)  # Instable à 500ms

#---------------------------------------------------------------------
# Boucle principale

while True:
    
    # Essayer de lance la fonction principale
    try:
        main()
        
    except Exception as e:
        print(f"--> Erreur dans main() : {e}")
        # Ajouter la dernière exception au fichier de log
        # Rediriger la sortie standard vers une variable "output"
        output = io.StringIO()
        # Imprimer les informations sur l'exception dans "output"
        sys.print_exception(e, output)
        with open('error.log', 'a') as f:
            f.write(f"--> Erreur dans main() : {e}\n")
            f.write(output.getvalue())
            f.write(f'--------------------\n')
            
            # Affichage des infos sur l'OLED
            oled.fill(0)
            oled.text("Erreur programme",0,8)
            oled.text("    relance",0,20)
            oled.text("  dans 1 min",0,40)
            oled.show()
        time.sleep(60)         # Attendre 60s avant de recommencer main()
        # machine.reset()

