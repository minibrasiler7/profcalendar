from datetime import date

# Vacances scolaires pour le canton de Vaud
# Source: https://www.vd.ch/themes/formation/scolarite-obligatoire/calendrier-scolaire-et-vacances/

VAUD_HOLIDAYS = {'2022-2023':
                     [{'name': "Vacances d'automne",
                       'start': date(2022, 10, 15),
                       'end': date(2022, 10, 30)},
                      {'name': "Vacances d'hiver",
                       'start': date(2022, 12, 24),
                       'end': date(2023, 1, 8)},
                      {'name': 'Relâches de février',
                       'start': date(2023, 2, 11),
                       'end': date(2023, 2, 19)},
                      {'name': 'Vacances de Pâques', 'start': date(2023, 4, 7),
                       'end': date(2023, 4, 23)},
                      {'name': "Pont de l'Ascension", 'start': date(2023, 5, 18),
                       'end': date(2023, 5, 19)},
                      {'name': 'Lundi de Pentecôte', 'start': date(2023, 5, 29),
                       'end': date(2023, 5, 29)}],

                 '2023-2024': [
                     {'name': "Vacances d'automne", 'start': date(2023, 10, 14),
                      'end': date(2023, 10, 29)},
                     {'name': "Vacances d'hiver", 'start': date(2023, 12, 23),
                      'end': date(2024, 1, 7)},
                     {'name': 'Relâches de février', 'start': date(2024, 2, 10),
                      'end': date(2024, 2, 18)},
                     {'name': 'Vacances de Pâques', 'start': date(2024, 3, 29),
                      'end': date(2024, 4, 14)},
                     {'name': "Pont de l'Ascension", 'start': date(2024, 5, 9),
                      'end': date(2024, 5, 10)},
                     {'name': 'Lundi de Pentecôte', 'start': date(2024, 5, 20),
                      'end': date(2024, 5, 20)}],

                 '2024-2025': [{'name': "Vacances d'automne", 'start': date(2024, 10, 12),
                                'end': date(2024, 10, 27)},
                               {'name': "Vacances d'hiver", 'start': date(2024, 12, 21),
                                'end': date(2025, 1, 5)},
                               {'name': 'Relâches de février', 'start': date(2025, 2, 15),
                                'end': date(2025, 2, 23)},
                               {'name': 'Vacances de Pâques', 'start': date(2025, 4, 12),
                                'end': date(2025, 4, 27)},
                               {'name': "Pont de l'Ascension", 'start': date(2025, 5, 29),
                                'end': date(2025, 5, 30)},
                               {'name': 'Lundi de Pentecôte', 'start': date(2025, 6, 9),
                                'end': date(2025, 6, 9)}],
                 '2025-2026': [
        {'name': "Vacances d'automne", 'start': date(2025, 10, 11), 'end': date(2025, 10, 26)},
        {'name': "Vacances d'hiver", 'start': date(2025, 12, 20), 'end': date(2026, 1, 4)},
        {'name': 'Relâches de février', 'start': date(2026, 2, 14), 'end': date(2026, 2, 22)},
        {'name': 'Vacances de Pâques', 'start': date(2026, 4, 3), 'end': date(2026, 4, 19)},
        {'name': "Pont de l'Ascension", 'start': date(2026, 5, 14), 'end': date(2026, 5, 15)},
        {'name': 'Lundi de Pentecôte', 'start': date(2026, 5, 25), 'end': date(2026, 5, 25)}],
                 '2026-2027': [{'name': "Vacances d'automne", 'start': date(2026, 10, 10),
                                'end': date(2026, 10, 25)},
                               {'name': "Vacances d'hiver", 'start': date(2026, 12, 24),
                                'end': date(2027, 1, 10)},
                               {'name': 'Relâches de février', 'start': date(2027, 2, 6),
                                'end': date(2027, 2, 14)},
                               {'name': 'Vacances de Pâques', 'start': date(2027, 3, 26),
                                'end': date(2027, 4, 11)},
                               {'name': "Pont de l'Ascension", 'start': date(2027, 5, 6),
                                'end': date(2027, 5, 7)},
                               {'name': 'Lundi de Pentecôte', 'start': date(2027, 5, 17),
                                'end': date(2027, 5, 17)}], '2027-2028': [
        {'name': "Vacances d'automne", 'start': date(2027, 10, 9), 'end': date(2027, 10, 24)},
        {'name': "Vacances d'hiver", 'start': date(2027, 12, 24), 'end': date(2028, 1, 9)},
        {'name': 'Relâches de février', 'start': date(2028, 2, 12), 'end': date(2028, 2, 20)},
        {'name': 'Vacances de Pâques', 'start': date(2028, 4, 11), 'end': date(2028, 4, 27)},
        {'name': "Pont de l'Ascension", 'start': date(2028, 5, 25), 'end': date(2028, 5, 26)},
        {'name': 'Lundi de Pentecôte', 'start': date(2028, 6, 5), 'end': date(2028, 6, 5)}],
                 '2028-2029': [{'name': "Vacances d'automne", 'start': date(2028, 10, 14),
                                'end': date(2028, 10, 29)},
                               {'name': "Vacances d'hiver", 'start': date(2028, 12, 23),
                                'end': date(2029, 1, 7)},
                               {'name': 'Relâches de février', 'start': date(2029, 2, 10),
                                'end': date(2029, 2, 18)},
                               {'name': 'Vacances de Pâques', 'start': date(2029, 4, 14),
                                'end': date(2029, 4, 30)},
                               {'name': "Pont de l'Ascension", 'start': date(2029, 5, 10),
                                'end': date(2029, 5, 11)},
                               {'name': 'Lundi de Pentecôte', 'start': date(2029, 5, 21),
                                'end': date(2029, 5, 21)}], '2029-2030': [
        {'name': "Vacances d'automne", 'start': date(2029, 10, 13), 'end': date(2029, 10, 28)},
        {'name': "Vacances d'hiver", 'start': date(2029, 12, 22), 'end': date(2030, 1, 6)},
        {'name': 'Relâches de février', 'start': date(2030, 2, 16), 'end': date(2030, 2, 24)},
        {'name': 'Vacances de Pâques', 'start': date(2030, 3, 30), 'end': date(2030, 4, 15)},
        {'name': "Pont de l'Ascension", 'start': date(2030, 5, 30), 'end': date(2030, 5, 31)},
        {'name': 'Lundi de Pentecôte', 'start': date(2030, 6, 10), 'end': date(2030, 6, 10)}],
                 '2030-2031': [{'name': "Vacances d'automne", 'start': date(2030, 10, 12),
                                'end': date(2030, 10, 27)},
                               {'name': "Vacances d'hiver", 'start': date(2030, 12, 21),
                                'end': date(2031, 1, 5)},
                               {'name': 'Relâches de février', 'start': date(2031, 2, 15),
                                'end': date(2031, 2, 23)},
                               {'name': 'Vacances de Pâques', 'start': date(2031, 4, 19),
                                'end': date(2031, 5, 5)},
                               {'name': "Pont de l'Ascension", 'start': date(2031, 5, 22),
                                'end': date(2031, 5, 23)},
                               {'name': 'Lundi de Pentecôte', 'start': date(2031, 6, 2),
                                'end': date(2031, 6, 2)}]}

def get_school_year(start_date):
    """Détermine l'année scolaire basée sur la date de début"""
    year = start_date.year
    if start_date.month < 8:  # Si avant août, c'est l'année scolaire précédente
        return f"{year-1}-{year}"
    else:
        return f"{year}-{year+1}"

def get_vaud_holidays(school_year_start):
    """Retourne les vacances scolaires vaudoises pour l'année scolaire donnée"""
    school_year = get_school_year(school_year_start)
    return VAUD_HOLIDAYS.get(school_year, [])
