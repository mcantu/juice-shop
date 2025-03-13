# Importación de módulos necesarios
import random
import config
import logger
import utils
import datacache
import security
from models import AddressModel, BasketModel, BasketItemModel, CardModel, ChallengeModel, ComplaintModel, DeliveryModel, FeedbackModel, MemoryModel, ProductModel, QuantityModel, RecycleModel, SecurityAnswerModel, SecurityQuestionModel, UserModel, WalletModel
from staticData import loadStaticChallengeData, loadStaticDeliveryData, loadStaticUserData, loadStaticSecurityQuestionsData
from mongodb import ordersCollection, reviewsCollection
from html import escape

# Función principal para la creación de datos
async def create_data():
    creators = [
        create_security_questions,
        create_users,
        create_challenges,
        create_random_fake_users,
        create_products,
        create_baskets,
        create_basket_items,
        create_anonymous_feedback,
        create_complaints,
        create_recycle_item,
        create_orders,
        create_quantity,
        create_wallet,
        create_delivery_methods,
        create_memories,
        prepare_filesystem
    ]

    for creator in creators:
        await creator()

# Función para crear desafíos
async def create_challenges():
    show_hints = config.get('challenges.showHints')
    show_mitigations = config.get('challenges.showMitigations')

    challenges = await loadStaticChallengeData()

    await asyncio.gather(
        *[
            create_challenge(challenge, show_hints, show_mitigations)
            for challenge in challenges
        ]
    )

async def create_challenge(challenge, show_hints, show_mitigations):
    name, category, description, difficulty, hint, hint_url, mitigation_url, key, disabled_env, tutorial, tags = challenge.values()
    is_challenge_enabled, disabled_because = utils.get_challenge_enablement_status(disabled_env)
    description = description.replace('juice-sh.op', config.get('application.domain'))
    description = description.replace('&lt;iframe width=&quot;100%&quot; height=&quot;166&quot; scrolling=&quot;no&quot; frameborder=&quot;no&quot; allow=&quot;autoplay&quot; src=&quot;https://w.soundcloud.com/player/?url=https%3A//api.soundcloud.com/tracks/771984076&amp;color=%23ff5500&amp;auto_play=true&amp;hide_related=false&amp;show_comments=true&amp;show_user=true&amp;show_reposts=false&amp;show_teaser=true&quot;&gt;&lt;/iframe&gt;', escape(config.get('challenges.xssBonusPayload')))
    hint = hint.replace("OWASP Juice Shop's", f"{config.get('application.name')}'s")

    try:
        datacache.challenges[key] = await ChallengeModel.create({
            'key': key,
            'name': name,
            'category': category,
            'tags': ','.join(tags) if tags else None,
            'description': description if is_challenge_enabled else f"{description} <em>(This challenge is <strong>potentially harmful</strong> on {disabled_because}!)</em>",
            'difficulty': difficulty,
            'solved': False,
            'hint': hint if show_hints else None,
            'hint_url': hint_url if show_hints else None,
            'mitigation_url': mitigation_url if show_mitigations else None,
            'disabled_env': disabled_because,
            'tutorial_order': tutorial['order'] if tutorial else None,
            'coding_challenge_status': 0
        })
    except Exception as err:
        logger.error(f"Could not insert Challenge {name}: {utils.get_error_message(err)}")

# Función para crear usuarios
async def create_users():
    users = await loadStaticUserData()

    await asyncio.gather(
        *[
            create_user(user)
            for user in users
        ]
    )

async def create_user(user):
    username, email, password, custom_domain, key, role, deleted_flag, profile_image, security_question, feedback, address, card, totp_secret, last_login_ip = user.values()
    try:
        complete_email = email if custom_domain else f"{email}@{config.get('application.domain')}"
        user = await UserModel.create({
            'username': username,
            'email': complete_email,
            'password': password,
            'role': role,
            'deluxe_token': security.deluxe_token(complete_email) if role == security.roles.deluxe else '',
            'profile_image': f"assets/public/images/uploads/{profile_image or ('defaultAdmin.png' if role == security.roles.admin else 'default.svg')}",
            'totp_secret': totp_secret,
            'last_login_ip': last_login_ip
        })
        datacache.users[key] = user
        if security_question:
            await create_security_answer(user.id, security_question['id'], security_question['answer'])
        if feedback:
            await create_feedback(user.id, feedback['comment'], feedback['rating'], user.email)
        if deleted_flag:
            await delete_user(user.id)
        if address:
            await create_addresses(user.id, address)
        if card:
            await create_cards(user.id, card)
    except Exception as err:
        logger.error(f"Could not insert User {key}: {utils.get_error_message(err)}")

# Función para crear billeteras
async def create_wallet():
    users = await loadStaticUserData()
    await asyncio.gather(
        *[
            WalletModel.create({
                'UserId': index + 1,
                'balance': user.get('walletBalance', 0)
            }).catch(lambda err: logger.error(f"Could not create wallet: {utils.get_error_message(err)}"))
            for index, user in enumerate(users)
        ]
    )

# Función para crear métodos de entrega
async def create_delivery_methods():
    deliveries = await loadStaticDeliveryData()

    await asyncio.gather(
        *[
            DeliveryModel.create({
                'name': delivery['name'],
                'price': delivery['price'],
                'deluxe_price': delivery['deluxePrice'],
                'eta': delivery['eta'],
                'icon': delivery['icon']
            }).catch(lambda err: logger.error(f"Could not insert Delivery Method: {utils.get_error_message(err)}"))
            for delivery in deliveries
        ]
    )

# Función para crear direcciones
async def create_addresses(UserId, addresses):
    await asyncio.gather(
        *[
            AddressModel.create({
                'UserId': UserId,
                'country': address['country'],
                'full_name': address['fullName'],
                'mobile_num': address['mobileNum'],
                'zip_code': address['zipCode'],
                'street_address': address['streetAddress'],
                'city': address['city'],
                'state': address.get('state')
            }).catch(lambda err: logger.error(f"Could not create address: {utils.get_error_message(err)}"))
            for address in addresses
        ]
    )

# Función para crear tarjetas
async def create_cards(UserId, cards):
    await asyncio.gather(
        *[
            CardModel.create({
                'UserId': UserId,
                'full_name': card['fullName'],
                'card_num': int(card['cardNum']),
                'exp_month': card['expMonth'],
                'exp_year': card['expYear']
            }).catch(lambda err: logger.error(f"Could not create card: {utils.get_error_message(err)}"))
            for card in cards
        ]
    )

# Función para eliminar usuarios
async def delete_user(user_id):
    await UserModel.destroy({'where': {'id': user_id}}).catch(lambda err: logger.error(f"Could not perform soft delete for the user {user_id}: {utils.get_error_message(err)}"))

# Función para eliminar productos
async def delete_product(product_id):
    await ProductModel.destroy({'where': {'id': product_id}}).catch(lambda err: logger.error(f"Could not perform soft delete for the product {product_id}: {utils.get_error_message(err)}"))

# Función para crear usuarios falsos aleatorios
async def create_random_fake_users():
    def get_generated_random_fake_user_email():
        random_domain = f"{make_random_string(4).lower()}.{make_random_string(2).lower()}"
        return f"{make_random_string(5).toLowerCase()}@{random_domain}"

    def make_random_string(length):
        text = ''
        possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

        for _ in range(length):
            text += possible.charAt(random.randint(0, len(possible) - 1))

        return text

    await asyncio.gather(
        *[
            UserModel.create({
                'email': get_generated_random_fake_user_email(),
                'password': make_random_string(5)
            })
            for _ in range(config.get('application.numberOfRandomFakeUsers'))
        ]
    )

# Función para crear cantidades
async def create_quantity():
    await asyncio.gather(
        *[
            QuantityModel.create({
                'ProductId': index + 1,
                'quantity': product.get('quantity', random.randint(30, 100)),
                'limit_per_user': product.get('limitPerUser')
            }).catch(lambda err: logger.error(f"Could not create quantity: {utils.get_error_message(err)}"))
            for index, product in enumerate(config.get('products'))
        ]
    )

# Función para crear memorias
async def create_memories():
    memories = [
        MemoryModel.create({
            'image_path': 'assets/public/images/uploads/😼-#zatschi-#whoneedsfourlegs-1572600969477.jpg',
            'caption': '😼 #zatschi #whoneedsfourlegs',
            'UserId': datacache.users['bjoernOwasp'].id
        }).catch(lambda err: logger.error(f"Could not create memory: {utils.get_error_message(err)}")),
        *[
            create_memory(memory)
            for memory in config.get('memories')
        ]
    ]

    await asyncio.gather(*memories)

async def create_memory(memory):
    tmp_image_file_name = memory['image']
    if utils.is_url(memory['image']):
        image_url = memory['image']
        tmp_image_file_name = utils.extract_filename(memory['image'])
        await utils.download_to_file(image_url, f"frontend/dist/frontend/assets/public/images/uploads/{tmp_image_file_name}")

    if memory.get('geoStalkingMetaSecurityQuestion') and memory.get('geoStalkingMetaSecurityAnswer'):
        await create_security_answer(datacache.users['john'].id, memory['geoStalkingMetaSecurityQuestion'], memory['geoStalkingMetaSecurityAnswer'])
        memory['user'] = 'john'

    if memory.get('geoStalkingVisualSecurityQuestion') and memory.get('geoStalkingVisualSecurityAnswer'):
        await create_security_answer(datacache.users['emma'].id, memory['geoStalkingVisualSecurityQuestion'], memory['geoStalkingVisualSecurityAnswer'])
        memory['user'] = 'emma'

    if not memory.get('user'):
        logger.warn(f"Could not find user for memory {memory['caption']}!")
        return

    user_id_of_memory = datacache.users[memory['user']].id
    if not user_id_of_memory:
        logger.warn(f"Could not find saved user for memory {memory['caption']}!")
        return

    await MemoryModel.create({
        'image_path': f"assets/public/images/uploads/{tmp_image_file_name}",
        'caption': memory['caption'],
        'UserId': user_id_of_memory
    }).catch(lambda err: logger.error(f"Could not create memory: {utils.get_error_message(err)}"))

# Función para crear productos
async def create_products():
    products = [
        customize_product(product)
        for product in config.get('products')
    ]

    await asyncio.gather(
        *[
            create_product(product)
            for product in products
        ]
    )

def customize_product(product):
    product['price'] = product.get('price', random.randint(1, 10))
    product['deluxe_price'] = product.get('deluxePrice', product['price'])
    product['description'] = product.get('description', 'Lorem ipsum dolor sit amet, consectetuer adipiscing elit.')
    product['image'] = product.get('image', 'undefined.png')

    if utils.is_url(product['image']):
        image_url = product['image']
        product['image'] = utils.extract_filename(product['image'])
        await utils.download_to_file(image_url, f"frontend/dist/frontend/assets/public/images/products/{product['image']}")

    return product

async def create_product(product):
    reviews = product.pop('reviews', [])
    use_for_christmas_special_challenge = product.pop('useForChristmasSpecialChallenge', False)
    url_for_product_tampering_challenge = product.pop('urlForProductTamperingChallenge', False)
    file_for_retrieve_blueprint_challenge = product.pop('fileForRetrieveBlueprintChallenge', False)
    deleted_date = product.pop('deletedDate', False)

    try:
        persisted_product = await ProductModel.create(product)
        if use_for_christmas_special_challenge:
            datacache.products['christmasSpecial'] = persisted_product
        if url_for_product_tampering_challenge:
            datacache.products['osaft'] = persisted_product
            await datacache.challenges['changeProductChallenge'].update({
                'description': customize_change_product_challenge(
                    datacache.challenges['changeProductChallenge'].description,
                    config.get('challenges.overwriteUrlForProductTamperingChallenge'),
                    persisted_product
                )
            })
        if file_for_retrieve_blueprint_challenge and datacache.challenges['retrieveBlueprintChallenge'].hint:
            await datacache.challenges['retrieveBlueprintChallenge'].update({
                'hint': customize_retrieve_blueprint_challenge(
                    datacache.challenges['retrieveBlueprintChallenge'].hint,
                    persisted_product
                )
            })
        if deleted_date:
            await delete_product(persisted_product.id)
    except Exception as err:
        logger.error(f"Could not insert Product {product['name']}: {utils.get_error_message(err)}")

    await asyncio.gather(
        *[
            reviewsCollection.insert({
                'message': review['text'],
                'author': datacache.users[review['author']].email,
                'product': persisted_product.id,
                'likes_count': 0,
                'liked_by': []
            }).catch(lambda err: logger.error(f"Could not insert Product Review {review['text']}: {utils.get_error_message(err)}"))
            for review in reviews
        ]
    )

def customize_change_product_challenge(description, custom_url, custom_product):
    custom_description = description.replace('OWASP SSL Advanced Forensic Tool (O-Saft)', custom_product['name'])
    custom_description = custom_description.replace('https://owasp.slack.com', custom_url)
    return custom_description

def customize_retrieve_blueprint_challenge(hint, custom_product):
    return hint.replace('OWASP Juice Shop Logo (3D-printed)', custom_product['name'])

# Función para crear cestas
async def create_baskets():
    baskets = [
        {'UserId': 1},
        {'UserId': 2},
        {'UserId': 3},
        {'UserId': 11},
        {'UserId': 16}
    ]

    await asyncio.gather(
        *[
            BasketModel.create(basket).catch(lambda err: logger.error(f"Could not insert Basket for UserId {basket['UserId']}: {utils.get_error_message(err)}"))
            for basket in baskets
        ]
    )

# Función para crear elementos de cestas
async def create_basket_items():
    basket_items = [
        {'BasketId': 1, 'ProductId': 1, 'quantity': 2},
        {'BasketId': 1, 'ProductId': 2, 'quantity': 3},
        {'BasketId': 1, 'ProductId': 3, 'quantity': 1},
        {'BasketId': 2, 'ProductId': 4, 'quantity': 2},
        {'BasketId': 3, 'ProductId': 4, 'quantity': 1},
        {'BasketId': 4, 'ProductId': 4, 'quantity': 2},
        {'BasketId': 5, 'ProductId': 3, 'quantity': 5},
        {'BasketId': 5, 'ProductId': 4, 'quantity': 2}
    ]

    await asyncio.gather(
        *[
            BasketItemModel.create(basket_item).catch(lambda err: logger.error(f"Could not insert BasketItem for BasketId {basket_item['BasketId']}: {utils.get_error_message(err)}"))
            for basket_item in basket_items
        ]
    )

# Función para crear comentarios anónimos
async def create_anonymous_feedback():
    feedbacks = [
        {'comment': "Incompetent customer support! Can't even upload photo of broken purchase!<br><em>Support Team: Sorry, only order confirmation PDFs can be attached to complaints!</em>", 'rating': 2},
        {'comment': 'This is <b>the</b> store for awesome stuff of all kinds!', 'rating': 4},
        {'comment': 'Never gonna buy anywhere else from now on! Thanks for the great service!', 'rating': 4},
        {'comment': 'Keep up the good work!', 'rating': 3}
    ]

    await asyncio.gather(
        *[
            create_feedback(None, feedback['comment'], feedback['rating'])
            for feedback in feedbacks
        ]
    )

# Función para crear comentarios
async def create_feedback(UserId, comment, rating, author=None):
    authored_comment = f"{comment} (***{author[3:]})" if author else f"{comment} (anonymous)"
    await FeedbackModel.create({'UserId': UserId, 'comment': authored_comment, 'rating': rating}).catch(lambda err: logger.error(f"Could not insert Feedback {authored_comment} mapped to UserId {UserId}: {utils.get_error_message(err)}"))

# Función para crear quejas
async def create_complaints():
    await ComplaintModel.create({
        'UserId': 3,
        'message': "I'll build my own eCommerce business! With Black Jack! And Hookers!"
    }).catch(lambda err: logger.error(f"Could not insert Complaint: {utils.get_error_message(err)}"))

# Función para crear elementos de reciclaje
async def create_recycle_item():
    recycles = [
        {'UserId': 2, 'quantity': 800, 'AddressId': 4, 'date': '2270-01-17', 'isPickup': True},
        {'UserId': 3, 'quantity': 1320, 'AddressId': 6, 'date': '2006-01-14', 'isPickup': True},
        {'UserId': 4, 'quantity': 120, 'AddressId': 1, 'date': '2018-04-16', 'isPickup': True},
        {'UserId': 1, 'quantity': 300, 'AddressId': 3, 'date': '2018-01-17', 'isPickup': True},
        {'UserId': 4, 'quantity': 350, 'AddressId': 1, 'date': '2018-03-17', 'isPickup': True},
        {'UserId': 3, 'quantity': 200, 'AddressId': 6, 'date': '2018-07-17', 'isPickup': True},
        {'UserId': 4, 'quantity': 140, 'AddressId': 1, 'date': '2018-03-19', 'isPickup': True},
        {'UserId': 1, 'quantity': 150, 'AddressId': 3, 'date': '2018-05-12', 'isPickup': True},
        {'UserId': 16, 'quantity': 500, 'AddressId': 2, 'date': '2019-02-18', 'isPickup': True}
    ]

    await asyncio.gather(
        *[
            create_recycle(recycle)
            for recycle in recycles
        ]
    )

async def create_recycle(data):
    await RecycleModel.create({
        'UserId': data['UserId'],
        'AddressId': data['AddressId'],
        'quantity': data['quantity'],
        'isPickup': data['isPickup'],
        'date': data['date']
    }).catch(lambda err: logger.error(f"Could not insert Recycling Model: {utils.get_error_message(err)}"))

# Función para crear preguntas de seguridad
async def create_security_questions():
    questions = await loadStaticSecurityQuestionsData()

    await asyncio.gather(
        *[
            SecurityQuestionModel.create({'question': question['question']}).catch(lambda err: logger.error(f"Could not insert SecurityQuestion {question['question']}: {utils.get_error_message(err)}"))
            for question in questions
        ]
    )

# Función para crear respuestas de seguridad
async def create_security_answer(UserId, SecurityQuestionId, answer):
    await SecurityAnswerModel.create({'SecurityQuestionId': SecurityQuestionId, 'UserId': UserId, 'answer': answer}).catch(lambda err: logger.error(f"Could not insert SecurityAnswer {answer} mapped to UserId {UserId}: {utils.get_error_message(err)}"))

# Función para crear órdenes
async def create_orders():
    products = config.get('products')
    basket1_products = [
        {'quantity': 3, 'id': products[0]['id'], 'name': products[0]['name'], 'price': products[0]['price'], 'total': products[0]['price'] * 3, 'bonus': round(products[0]['price'] / 10) * 3},
        {'quantity': 1, 'id': products[1]['id'], 'name': products[1]['name'], 'price': products[1]['price'], 'total': products[1]['price'] * 1, 'bonus': round(products[1]['price'] / 10) * 1}
    ]

    basket2_products = [
        {'quantity': 3, 'id': products[2]['id'], 'name': products[2]['name'], 'price': products[2]['price'], 'total': products[2]['price'] * 3, 'bonus': round(products[2]['price'] / 10) * 3}
    ]

    basket3_products = [
        {'quantity': 3, 'id': products[0]['id'], 'name': products[0]['name'], 'price': products[0]['price'], 'total': products[0]['price'] * 3, 'bonus': round(products[0]['price'] / 10) * 3},
        {'quantity': 5, 'id': products[3]['id'], 'name': products[3]['name'], 'price': products[3]['price'], 'total': products[3]['price'] * 5, 'bonus': round(products[3]['price'] / 10) * 5}
    ]

    admin_email = f"admin@{config.get('application.domain')}"
    orders = [
        {
            'order_id': f"{security.hash(admin_email)[:4]}-{utils.random_hex_string(16)}",
            'email': admin_email.replace(/[aeiou]/gi, '*'),
            'total_price': basket1_products[0]['total'] + basket1_products[1]['total'],
            'bonus': basket1_products[0]['bonus'] + basket1_products[1]['bonus'],
            'products': basket1_products,
            'eta': str(random.randint(1, 5)),
            'delivered': False
        },
        {
            'order_id': f"{security.hash(admin_email)[:4]}-{utils.random_hex_string(16)}",
            'email': admin_email.replace(/[aeiou]/gi, '*'),
            'total_price': basket2_products[0]['total'],
            'bonus': basket2_products[0]['bonus'],
            'products': basket2_products,
            'eta': '0',
            'delivered': True
        },
        {
            'order_id': f"{security.hash('demo')[:4]}-{utils.random_hex_string(16)}",
            'email': 'd*m*',
            'total_price': basket3_products[0]['total'] + basket3_products[1]['total'],
            'bonus': basket3_products[0]['bonus'] + basket3_products[1]['bonus'],
            'products': basket3_products,
            'eta': '0',
            'delivered': True
        }
    ]

    await asyncio.gather(
        *[
            ordersCollection.insert(order).catch(lambda err: logger.error(f"Could not insert Order {order['order_id']}: {utils.get_error_message(err)}"))
            for order in orders
        ]
    )

# Función para preparar el sistema de archivos
async def prepare_filesystem():
    replace({
        'regex': 'http://localhost:3000',
        'replacement': config.get('server.baseUrl'),
        'paths': ['.well-known/csaf/provider-metadata.json'],
        'recursive': True,
        'silent': True
    })
