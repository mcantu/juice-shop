# Definir funciones necesarias para las utilidades de los desafíos en Python

from datetime import datetime
from typing import Callable, Dict, Any
from sqlalchemy import update
from models.challenge import ChallengeModel
import logger
import config
import sanitize_html
import colors
import utils
from antiCheat import calculate_cheat_score, calculate_find_it_cheat_score, calculate_fix_it_cheat_score
import webhook
import accuracy
from socketio import Server
from html import unescape
from data.datacache import challenges, notifications

global_with_socketio = {
    "io": None
}

# Resolver el desafío si se cumple el criterio
def solve_if(challenge: Any, criteria: Callable[[], Any], is_restore: bool = False):
    if not_solved(challenge) and criteria():
        solve(challenge, is_restore)

# Resolver el desafío
def solve(challenge: Any, is_restore: bool = False):
    challenge.solved = True
    challenge.save().then(lambda solved_challenge: handle_solved_challenge(solved_challenge, is_restore))

# Manejar el desafío resuelto
def handle_solved_challenge(solved_challenge: Dict[str, Any], is_restore: bool):
    logger.info(f"{'Restored' if is_restore else 'Solved'} {solved_challenge['difficulty']}-star {colors.cyan(solved_challenge['key'])} ({solved_challenge['name']})")
    send_notification(solved_challenge, is_restore)
    if not is_restore:
        cheat_score = calculate_cheat_score(solved_challenge)
        if process.env.SOLUTIONS_WEBHOOK:
            webhook.notify(solved_challenge, cheat_score).catch(lambda error: logger.error(f"Webhook notification failed: {colors.red(utils.get_error_message(error))}"))

# Enviar notificación del desafío resuelto
def send_notification(challenge: Dict[str, Any], is_restore: bool):
    if not not_solved(challenge):
        flag = utils.ctf_flag(challenge['name'])
        notification = {
            "key": challenge['key'],
            "name": challenge['name'],
            "challenge": f"{challenge['name']} ({unescape(sanitize_html(challenge['description'], {'allowed_tags': [], 'allowed_attributes': {}}))})",
            "flag": flag,
            "hidden": not config.get('challenges.showSolvedNotifications'),
            "is_restore": is_restore
        }
        was_previously_shown = any(n['key'] == challenge['key'] for n in notifications)
        notifications.append(notification)

        if global_with_socketio["io"] and (is_restore or not was_previously_shown):
            global_with_socketio["io"].emit('challenge solved', notification)

# Enviar notificación del desafío de codificación
def send_coding_challenge_notification(challenge: Dict[str, Any]):
    if challenge['coding_challenge_status'] > 0:
        notification = {
            "key": challenge['key'],
            "coding_challenge_status": challenge['coding_challenge_status']
        }
        if global_with_socketio["io"]:
            global_with_socketio["io"].emit('code challenge solved', notification)

# Verificar si el desafío no está resuelto
def not_solved(challenge: Any) -> bool:
    return challenge and not challenge.solved

# Encontrar desafío por nombre
def find_challenge_by_name(challenge_name: str) -> Any:
    for c in challenges:
        if challenges[c].name == challenge_name:
            return challenges[c]
    logger.warn(f"Missing challenge with name: {challenge_name}")

# Encontrar desafío por ID
def find_challenge_by_id(challenge_id: int) -> Any:
    for c in challenges:
        if challenges[c].id == challenge_id:
            return challenges[c]
    logger.warn(f"Missing challenge with id: {challenge_id}")

# Resolver la fase "Find It" del desafío de codificación
async def solve_find_it(key: str, is_restore: bool = False):
    solved_challenge = challenges[key]
    await update(ChallengeModel).where(ChallengeModel.key == key, ChallengeModel.coding_challenge_status < 2).values(coding_challenge_status=1)
    logger.info(f"{'Restored' if is_restore else 'Solved'} 'Find It' phase of coding challenge {colors.cyan(solved_challenge.key)} ({solved_challenge.name})")
    if not is_restore:
        accuracy.store_find_it_verdict(solved_challenge.key, True)
        accuracy.calculate_find_it_accuracy(solved_challenge.key)
        await calculate_find_it_cheat_score(solved_challenge)
        send_coding_challenge_notification({"key": key, "coding_challenge_status": 1})

# Resolver la fase "Fix It" del desafío de codificación
async def solve_fix_it(key: str, is_restore: bool = False):
    solved_challenge = challenges[key]
    await update(ChallengeModel).where(ChallengeModel.key == key).values(coding_challenge_status=2)
    logger.info(f"{'Restored' if is_restore else 'Solved'} 'Fix It' phase of coding challenge {colors.cyan(solved_challenge.key)} ({solved_challenge.name})")
    if not is_restore:
        accuracy.store_fix_it_verdict(solved_challenge.key, True)
        accuracy.calculate_fix_it_accuracy(solved_challenge.key)
        await calculate_fix_it_cheat_score(solved_challenge)
        send_coding_challenge_notification({"key": key, "coding_challenge_status": 2})
