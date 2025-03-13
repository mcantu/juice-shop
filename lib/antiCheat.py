# Definir funciones necesarias para el anti-cheat en Python

import config
import colors
from vulnCodeSnippet import retrieve_code_snippet
from vulnCodeFixes import read_fixes
from data.types import Challenge
from codingChallenges import get_code_challenges
import logger
from express import NextFunction, Request, Response
import utils
import median

coupled_challenges = {
    'loginAdminChallenge': ['weakPasswordChallenge'],
    'nullByteChallenge': ['easterEggLevelOneChallenge', 'forgottenDevBackupChallenge', 'forgottenBackupChallenge', 'misplacedSignatureFileChallenge'],
    'deprecatedInterfaceChallenge': ['uploadTypeChallenge', 'xxeFileDisclosureChallenge', 'xxeDosChallenge'],
    'uploadSizeChallenge': ['uploadTypeChallenge', 'xxeFileDisclosureChallenge', 'xxeDosChallenge'],
    'uploadTypeChallenge': ['uploadSizeChallenge', 'xxeFileDisclosureChallenge', 'xxeDosChallenge']
}
trivial_challenges = ['errorHandlingChallenge', 'privacyPolicyChallenge', 'closeNotificationsChallenge']

solves = [{'challenge': {}, 'phase': 'server start', 'timestamp': datetime.now(), 'cheat_score': 0}]

pre_solve_interactions = [
    {'challenge_key': 'missingEncodingChallenge', 'url_fragments': ['/assets/public/images/uploads/%F0%9F%98%BC-'], 'interactions': [False]},
    {'challenge_key': 'directoryListingChallenge', 'url_fragments': ['/ftp'], 'interactions': [False]},
    {'challenge_key': 'easterEggLevelOneChallenge', 'url_fragments': ['/ftp', '/ftp/eastere.gg'], 'interactions': [False, False]},
    {'challenge_key': 'easterEggLevelTwoChallenge', 'url_fragments': ['/ftp', '/gur/qrif/ner/fb/shaal/gurl/uvq/na/rnfgre/rtt/jvguva/gur/rnfgre/rtt'], 'interactions': [False, False]},
    {'challenge_key': 'forgottenDevBackupChallenge', 'url_fragments': ['/ftp', '/ftp/package.json.bak'], 'interactions': [False, False]},
    {'challenge_key': 'forgottenBackupChallenge', 'url_fragments': ['/ftp', '/ftp/coupons_2013.md.bak'], 'interactions': [False, False]},
    {'challenge_key': 'loginSupportChallenge', 'url_fragments': ['/ftp', '/ftp/incident-support.kdbx'], 'interactions': [False, False]},
    {'challenge_key': 'misplacedSignatureFileChallenge', 'url_fragments': ['/ftp', '/ftp/suspicious_errors.yml'], 'interactions': [False, False]},
    {'challenge_key': 'recChallenge', 'url_fragments': ['/api-docs', '/b2b/v2/orders'], 'interactions': [False, False]},
    {'challenge_key': 'rceOccupyChallenge', 'url_fragments': ['/api-docs', '/b2b/v2/orders'], 'interactions': [False, False]}
]

def check_for_pre_solve_interactions():
    def middleware(req: Request, res: Response, next: NextFunction):
        for pre_solve_interaction in pre_solve_interactions:
            for i in range(len(pre_solve_interaction['url_fragments'])):
                if utils.ends_with(req.url, pre_solve_interaction['url_fragments'][i]):
                    pre_solve_interaction['interactions'][i] = True
        next()
    return middleware

def calculate_cheat_score(challenge: Challenge):
    timestamp = datetime.now()
    cheat_score = 0
    time_factor = 2
    time_factor *= (1 if config.get('challenges.showHints') else 1.5)
    time_factor *= (0.5 if challenge.tutorial_order and config.get('hackingInstructor.isEnabled') else 1)
    if are_coupled(challenge, previous()['challenge']) or is_trivial(challenge):
        time_factor = 0

    minutes_expected_to_solve = challenge.difficulty * time_factor
    minutes_since_previous_solve = (timestamp - previous()['timestamp']).total_seconds() / 60
    cheat_score += max(0, 1 - (minutes_since_previous_solve / minutes_expected_to_solve))

    pre_solve_interaction = next((psi for psi in pre_solve_interactions if psi['challenge_key'] == challenge.key), None)
    percent_preceding_interaction = -1
    if pre_solve_interaction:
        percent_preceding_interaction = sum(pre_solve_interaction['interactions']) / len(pre_solve_interaction['interactions'])
        multiplier_for_missing_expected_interaction = 1 + max(0, 1 - percent_preceding_interaction) / 2
        cheat_score *= multiplier_for_missing_expected_interaction
        cheat_score = min(1, cheat_score)

    logger.info(f"Cheat score for {'coupled ' if are_coupled(challenge, previous()['challenge']) else ('trivial ' if is_trivial(challenge) else '')}{'tutorial ' if challenge.tutorial_order else ''}{colors.cyan(challenge.key)} solved in {round(minutes_since_previous_solve)}min (expected ~{minutes_expected_to_solve}min) with{'out' if not config.get('challenges.showHints') else ''} hints allowed{f' and {percent_preceding_interaction * 100}% expected preceding URL interaction' if percent_preceding_interaction > -1 else ''}: {colors.green(str(cheat_score)) if cheat_score < 0.33 else (colors.yellow(str(cheat_score)) if cheat_score < 0.66 else colors.red(str(cheat_score)))}")
    solves.append({'challenge': challenge, 'phase': 'hack it', 'timestamp': timestamp, 'cheat_score': cheat_score})
    return cheat_score

async def calculate_find_it_cheat_score(challenge: Challenge):
    timestamp = datetime.now()
    time_factor = 0.001
    time_factor *= (0.5 if challenge.key == 'scoreBoardChallenge' and config.get('hackingInstructor.isEnabled') else 1)
    cheat_score = 0

    code_snippet = await retrieve_code_snippet(challenge.key)
    if code_snippet is None:
        return 0
    snippet, vuln_lines = code_snippet['snippet'], code_snippet['vuln_lines']
    time_factor *= len(vuln_lines)
    identical_solved = await check_for_identical_solved_challenge(challenge)
    if identical_solved:
        time_factor = 0.8 * time_factor
    minutes_expected_to_solve = math.ceil(len(snippet) * time_factor)
    minutes_since_previous_solve = (timestamp - previous()['timestamp']).total_seconds() / 60
    cheat_score += max(0, 1 - (minutes_since_previous_solve / minutes_expected_to_solve))

    logger.info(f"Cheat score for 'Find it' phase of {'tutorial ' if challenge.key == 'scoreBoardChallenge' and config.get('hackingInstructor.isEnabled') else ''}{colors.cyan(challenge.key)} solved in {round(minutes_since_previous_solve)}min (expected ~{minutes_expected_to_solve}min): {colors.green(str(cheat_score)) if cheat_score < 0.33 else (colors.yellow(str(cheat_score)) if cheat_score < 0.66 else colors.red(str(cheat_score)))}")
    solves.append({'challenge': challenge, 'phase': 'find it', 'timestamp': timestamp, 'cheat_score': cheat_score})

    return cheat_score

async def calculate_fix_it_cheat_score(challenge: Challenge):
    timestamp = datetime.now()
    cheat_score = 0

    fixes = read_fixes(challenge.key)['fixes']
    minutes_expected_to_solve = math.floor(len(fixes) / 2)
    minutes_since_previous_solve = (timestamp - previous()['timestamp']).total_seconds() / 60
    cheat_score += max(0, 1 - (minutes_since_previous_solve / minutes_expected_to_solve))

    logger.info(f"Cheat score for 'Fix it' phase of {colors.cyan(challenge.key)} solved in {round(minutes_since_previous_solve)}min (expected ~{minutes_expected_to_solve}min): {colors.green(str(cheat_score)) if cheat_score < 0.33 else (colors.yellow(str(cheat_score)) if cheat_score < 0.66 else colors.red(str(cheat_score)))}")
    solves.append({'challenge': challenge, 'phase': 'fix it', 'timestamp': timestamp, 'cheat_score': cheat_score})
    return cheat_score

def total_cheat_score():
    return median([solve['cheat_score'] for solve in solves]) if len(solves) > 1 else 0

def are_coupled(challenge: Challenge, previous_challenge: Challenge):
    return challenge.key in coupled_challenges and previous_challenge.key in coupled_challenges[challenge.key] or previous_challenge.key in coupled_challenges and challenge.key in coupled_challenges[previous_challenge.key]

def is_trivial(challenge: Challenge):
    return challenge.key in trivial_challenges

def previous():
    return solves[-1]

async def check_for_identical_solved_challenge(challenge: Challenge):
    coding_challenges = await get_code_challenges()
    if challenge.key not in coding_challenges:
        return False

    coding_challenges_to_compare_to = coding_challenges[challenge.key]
    if not coding_challenges_to_compare_to['snippet']:
        return False
    snippet_to_compare_to = coding_challenges_to_compare_to['snippet']

    for challenge_key, snippet in coding_challenges.items():
        if challenge_key == challenge.key:
            continue

        if snippet == snippet_to_compare_to:
            for solved_challenge in solves:
                if solved_challenge['phase'] == 'find it':
                    return True
    return False
