# Definir funciones necesarias para el cálculo de precisión en Python

import logging
import colors

solves = {}

# Almacenar el veredicto de "find it"
def store_find_it_verdict(challenge_key, verdict):
    store_verdict(challenge_key, 'find it', verdict)

# Almacenar el veredicto de "fix it"
def store_fix_it_verdict(challenge_key, verdict):
    store_verdict(challenge_key, 'fix it', verdict)

# Calcular la precisión de "find it"
def calculate_find_it_accuracy(challenge_key):
    return calculate_accuracy(challenge_key, 'find it')

# Calcular la precisión de "fix it"
def calculate_fix_it_accuracy(challenge_key):
    return calculate_accuracy(challenge_key, 'fix it')

# Calcular la precisión total de "find it"
def total_find_it_accuracy():
    return total_accuracy('find it')

# Calcular la precisión total de "fix it"
def total_fix_it_accuracy():
    return total_accuracy('fix it')

# Obtener los intentos de "find it"
def get_find_it_attempts(challenge_key):
    return solves[challenge_key]['attempts']['find it'] if challenge_key in solves else 0

# Calcular la precisión total
def total_accuracy(phase):
    sum_accuracy = 0
    total_solved = 0
    for key, value in solves.items():
        if value[phase]:
            sum_accuracy += 1 / value['attempts'][phase]
            total_solved += 1
    return sum_accuracy / total_solved

# Calcular la precisión
def calculate_accuracy(challenge_key, phase):
    accuracy = 0
    if solves[challenge_key][phase]:
        accuracy = 1 / solves[challenge_key]['attempts'][phase]
    logging.info(f"Accuracy for '{'Fix It' if phase == 'fix it' else 'Find It'}' phase of coding challenge {colors.cyan(challenge_key)}: {colors.green(str(accuracy)) if accuracy > 0.5 else (colors.yellow(str(accuracy)) if accuracy > 0.25 else colors.red(str(accuracy)))}")
    return accuracy

# Almacenar el veredicto
def store_verdict(challenge_key, phase, verdict):
    if challenge_key not in solves:
        solves[challenge_key] = {'find it': False, 'fix it': False, 'attempts': {'find it': 0, 'fix it': 0}}
    if not solves[challenge_key][phase]:
        solves[challenge_key][phase] = verdict
        solves[challenge_key]['attempts'][phase] += 1
