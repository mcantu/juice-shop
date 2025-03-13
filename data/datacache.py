# Definición de estructuras de datos y funciones necesarias en Python

# Diccionarios para almacenar datos
challenges = {}
users = {}
products = {}
feedback = {}
baskets = {}
basketItems = {}
complaints = {}

# Clase para notificaciones
class Notification:
    def __init__(self, key, name, challenge, flag, hidden, isRestore):
        self.key = key
        self.name = name
        self.challenge = challenge
        self.flag = flag
        self.hidden = hidden
        self.isRestore = isRestore

# Lista de notificaciones
notifications = []

# Variable para almacenar el archivo de desafío de plano
retrieveBlueprintChallengeFile = None

# Función para establecer el archivo de desafío de plano
def setRetrieveBlueprintChallengeFile(retrieveBlueprintChallengeFileArg):
    global retrieveBlueprintChallengeFile
    retrieveBlueprintChallengeFile = retrieveBlueprintChallengeFileArg
