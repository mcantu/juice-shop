# Importar el módulo pymongo para la conexión con MongoDB
from pymongo import MongoClient

# Crear una instancia del cliente de MongoDB
client = MongoClient('mongodb://localhost:27017/')

# Seleccionar la base de datos
db = client['juice_shop']

# Seleccionar las colecciones
reviews_collection = db['reviews']
orders_collection = db['orders']

# Función para insertar un documento en la colección de reseñas
def insert_review(review):
    """
    Inserta un documento en la colección de reseñas.
    :param review: Diccionario que representa la reseña a insertar.
    """
    reviews_collection.insert_one(review)

# Función para insertar un documento en la colección de órdenes
def insert_order(order):
    """
    Inserta un documento en la colección de órdenes.
    :param order: Diccionario que representa la orden a insertar.
    """
    orders_collection.insert_one(order)

# Función para obtener todas las reseñas
def get_all_reviews():
    """
    Obtiene todas las reseñas de la colección.
    :return: Lista de diccionarios que representan las reseñas.
    """
    return list(reviews_collection.find())

# Función para obtener todas las órdenes
def get_all_orders():
    """
    Obtiene todas las órdenes de la colección.
    :return: Lista de diccionarios que representan las órdenes.
    """
    return list(orders_collection.find())
