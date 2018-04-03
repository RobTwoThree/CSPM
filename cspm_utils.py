
from pokemonlist import pokemon, pokejson, pokejson_by_name
import datetime
import calendar
import time

def find_pokemon_id(name):
    if name == 'Egg':
        return 0
    elif name == 'Nidoran-F':
        return 29
    elif name == 'Nidoran-M':
        return 32
    elif name == 'Mr-Mime':
        return 122
    elif name == 'Ho-Oh':
        return 250
    elif name == 'Mime-Jr':
        return 439
    else:
        return int(pokejson_by_name.get(name, 0))

def get_time(minute):
    future = datetime.datetime.utcnow() + datetime.timedelta(minutes=minute)
    return calendar.timegm(future.timetuple())

def get_team_id(raw_team):
    gym_team_id = 0

    if raw_team.isnumeric() and ( raw_team >= '0' ) and ( raw_team <= '3' ):
        gym_team_id = int(raw_team)
    else:
        team_name = str(raw_team).capitalize()
        if ( team_name in 'Mystic' ) or ( team_name in 'Blue' ):
           gym_team_id = 1
        elif ( team_name in 'Valor' ) or ( team_name in 'Red' ):
           gym_team_id = 2
        elif ( team_name in 'Instinct')  or ( team_name in 'Yellow' ):
           gym_team_id = 3
        else:
           gym_team_id = 0
    return gym_team_id

def get_team_name(team_id):
    if ( team_id == 1 ):
        team_name = 'Mystic'
    elif ( team_id == 2 ):
        team_name = 'Valor'
    elif ( team_id == 3 ):
        team_name = 'Instinct'
    else:
        team_name = 'Unknown'
    return team_name

MYSTIC_COLOR = 0x005ef7
VALOR_COLOR = 0xdb0000
INSTINCT_COLOR = 0xfcd00a
UNKNOWN_COLOR = 0xbcbcbc

def get_team_color(team_id):
    if ( team_id == 1 ):
        color = MYSTIC_COLOR
    elif ( team_id == 2 ):
        color = VALOR_COLOR
    elif ( team_id == 3 ):
        color = INSTINCT_COLOR
    else:
        color = UNKNOWN_COLOR
    return color

LEVEL_1_2_EGG_URL = 'https://raw.githubusercontent.com/ZeChrales/PogoAssets/master/static_assets/png/ic_raid_egg_normal.png'
LEVEL_3_4_EGG_URL = 'https://raw.githubusercontent.com/ZeChrales/PogoAssets/master/static_assets/png/ic_raid_egg_rare.png'
LEVEL_5_EGG_URL = 'https://raw.githubusercontent.com/ZeChrales/PogoAssets/master/static_assets/png/ic_raid_egg_legendary.png'

def get_egg_url(egg_level):
    if ( egg_level == '1' ) or ( egg_level == '2' ):
        egg_url = LEVEL_1_2_EGG_URL
    elif ( egg_level == '3' ) or ( egg_level == '4' ):
        egg_url = LEVEL_3_4_EGG_URL
    else:
        egg_url = LEVEL_5_EGG_URL

    return egg_url
