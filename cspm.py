import MySQLdb
import discord
from discord.ext import commands
import asyncio
from pokemonlist import pokemon, pokejson, pokejson_by_name
from cspm_utils import find_pokemon_id, get_team_id, get_team_name, get_team_color, get_egg_url
from config import bot_channel, token, host, user, password, database, website, log_channel, instance_id
import datetime
import calendar
import time

bot = commands.Bot(command_prefix = '!') # Set prefix to !

database = MySQLdb.connect(host,user,password,database)

cursor = database.cursor()

print('CSPM Started for ' + str(instance_id))

@bot.command(pass_context=True)
async def raid(ctx, raw_gym_name, raw_pokemon_name, raw_raid_level, raw_time_remaining, raw_team):
    if ctx and ctx.message.channel.id == str(bot_channel):
        pokemon_name = str(raw_pokemon_name).capitalize()
        pokemon_id = find_pokemon_id(pokemon_name)
        remaining_time = get_time(int(raw_time_remaining))
        current_time = datetime.datetime.utcnow()
        gym_team_id = get_team_id(raw_team)
        database.ping(True)

        try:
            if raw_gym_name.isnumeric():
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE id LIKE '" + str(raw_gym_name) + "';")
            else:
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE name LIKE '%" + str(raw_gym_name) + "%';")
            gym_data = cursor.fetchall()
            count = cursor.rowcount

            # Single gym_id is returned so check if a raid exists for it
            if ( count == 1 ):
                gym_id = gym_data[0][0]
                gym_name = gym_data[0][1]
                cursor.execute("SELECT id, fort_id, time_end FROM raids WHERE fort_id='" + str(gym_id) + "' AND time_end>'" + str(calendar.timegm(current_time.timetuple())) + "';")
                raid_data = cursor.fetchall()
                raid_count = cursor.rowcount

                if (raid_count):
                    raid_id = raid_data[0][0]
                    raid_fort_id = raid_data[0][1]
                    raid_time_end = raid_data[0][2]
            else:
                gym_names = ''
                raid_count = 0
                for gym in gym_data:
                    gym_names += str(gym[0]) + ': ' + gym[1] + ' (' + str(gym[2]) + ', ' + str(gym[3]) + ')\n'

            if ( pokemon_name == "Egg" ):
                est_end_time = remaining_time + 2700

                if (raid_count):
                    cursor.execute("UPDATE raids SET level='" + str(raw_raid_level) + "', time_battle='" + str(remaining_time) + "', time_end='" + str(est_end_time) + "' WHERE id='" + str(raid_id)+ "';")
                    await bot.say('Updated **Level ' + str(raw_raid_level) + ' ' + str(pokemon_name) + '**' +
                                  '\nGym: **' + str(gym_id) + ': ' + str(gym_name) + ' Gym' + '**' +
                                  '\nHatches: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                  '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(est_end_time))) + '**' +
                                  '\nTeam: **' + str(get_team_name(gym_team_id)) + '**')
                else:
                    cursor.execute("INSERT INTO raids("
                                   "id, external_id, fort_id , level, "
                                   "pokemon_id, move_1, move_2, time_spawn, "
                                   "time_battle, time_end, cp)"
                                   "VALUES "
                                   "(null, null, " + str(gym_id) + ", "
                                   + str(raw_raid_level) + ", " + str(pokemon_id) + ", null, null, "
                                   "null, " + str(remaining_time) + ", " + str(est_end_time) + ", null);")
                    await bot.say('Added new **Level ' + str(raw_raid_level) + ' ' + str(pokemon_name) + '**' +
                                  '\nGym: **' + str(gym_name) + ' Gym' + '**' +
                                  '\nHatches: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                  '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(est_end_time))) + '**' +
                                  '\nTime Left: **' + str(raw_time_remaining) + ' minutes**' +
                                  '\nTeam: **' + str(get_team_name(gym_team_id)) + '**')
                    raid_embed=discord.Embed(
                        title='**Level ' + str(raw_raid_level) + ' Egg**',
                        description='Gym: **' + str(gym_name) + ' Gym**' +
                                    '\nHatches: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                    '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(est_end_time))) + '**' +
                                    '\nTeam: **' + str(get_team_name(gym_team_id))+ '**' +
                                    '\nReported by: __' + str(ctx.message.author.name) + '__' +
                                    '\n\nhttps://www.google.com/maps?q=loc:' + str(gym_data[0][2]) + ',' + str(gym_data[0][3]),
                        color=team_color(gym_team_id)
                    )
                    thumbnail_image_url = get_egg_url(raw_raid_level)
                    raid_embed.set_thumbnail(url=thumbnail_image_url)
                    await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)

                    print(str(ctx.message.author.name) + ' reported a ' + str(pokemon_name) + ' at ' + str(gym_name) + ' gym with ' + str(raw_time_remaining) + ' minutes left.')
            else:
                # Update Egg to a hatched Raid Boss
                if (raid_count):
                    cursor.execute("UPDATE raids SET pokemon_id='" + str(pokemon_id) + "', level='" + str(raw_raid_level) + "', time_battle='" + str(calendar.timegm(current_time.timetuple())) + "', time_end='" + str(remaining_time) + "' WHERE id='" + str(raid_id)+ "';")
                    await bot.say('Updated **Level ' + str(raw_raid_level) + ' Egg to ' + str(pokemon_name) + ' Raid' + '**' +
                                  '\nGym: **' + str(gym_id) + ': ' + str(gym_name) + ' Gym' + '**' +
                                  '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                  '\nTeam: **' + str(get_team_name(gym_team_id)) + '**')

                    raid_embed=discord.Embed(
                        title='**Level ' + str(raw_raid_level) + ' ' + str(pokemon_name) + ' Raid**',
                        description='Gym: **' + str(gym_name) + ' Gym**' +
                                    '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                    '\nTeam: **' + str(get_team_name(gym_team_id))+ '**' +
                                    '\nReported by: __' + str(ctx.message.author.name) + '__' +
                                    '\n\nhttps://www.google.com/maps?q=loc:' + str(gym_data[0][2]) + ',' + str(gym_data[0][3]),
                        color=team_color(gym_team_id)
                    )
                    thumbnail_image_url = 'https://bitbucket.org/anzmap/sprites/raw/HEAD/' + str(pokemon_id) + '.png'
                    raid_embed.set_thumbnail(url=thumbnail_image_url)
                    await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)

                    print(str(ctx.message.author.name) + ' updated the ' + str(raw_raid_level) + ' Egg to ' + str(pokemon_name) + ' Raid at ' + str(gym_name) + ' gym (' + str(get_team_name(gym_team_id)) + ') with ' + str(raw_time_remaining) + ' minutes left.')

                else:
                    cursor.execute("INSERT INTO raids("
                                   "id, external_id, fort_id , level, "
                                   "pokemon_id, move_1, move_2, time_spawn, "
                                   "time_battle, time_end, cp)"
                                   "VALUES "
                                   "(null, null, " + str(gym_id) + ", "
                                   + str(raw_raid_level) + ", " + str(pokemon_id) + ", null, null, "
                                   "null, " + str(calendar.timegm(current_time.timetuple())) + ", " + str(remaining_time) + ", null);")
                    await bot.say('Added new **Level ' + str(raw_raid_level) + ' ' + str(pokemon_name) + ' Raid' + '**' +
                                  '\nGym: **' + str(gym_id) + ': ' + str(gym_name) + ' Gym**' +
                                  '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                  '\nTime Left: **' + str(raw_time_remaining) + ' minutes**' +
                                  '\nTeam: **' + str(get_team_name(gym_team_id)) + '**')

                    raid_embed=discord.Embed(
                        title='**Level ' + str(raw_raid_level) + ' ' + str(pokemon_name) + ' Raid**',
                        description='Gym: **' + str(gym_name) + ' Gym**' +
                                    '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                    '\nTeam: **' + str(get_team_name(gym_team_id))+ '**' +
                                    '\nReported by: __' + str(ctx.message.author.name) + '__' +
                                    '\n\nhttps://www.google.com/maps?q=loc:' + str(gym_data[0][2]) + ',' + str(gym_data[0][3]),
                        color=team_color(gym_team_id)
                    )
                    thumbnail_image_url = 'https://bitbucket.org/anzmap/sprites/raw/HEAD/' + str(pokemon_id) + '.png'
                    raid_embed.set_thumbnail(url=thumbnail_image_url)
                    await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)
                    print(str(ctx.message.author.name) + ' reported a ' + str(pokemon_name) + ' raid at ' + str(gym_name) + ' gym (' + str(get_team_name(gym_team_id)) + ') with ' + str(raw_time_remaining) + ' minutes left.')
            # Check if fort_id exists in fort_sightings.  If so update the entry, otherwise enter as a new entry.
            cursor.execute("SELECT id, fort_id, team FROM fort_sightings WHERE fort_id='" + str(gym_id) + "';")
            fs_count = cursor.rowcount
            if (fs_count):
                cursor.execute("UPDATE fort_sightings SET team='" + str(gym_team_id) + "' WHERE fort_id='" + str(gym_id) + "';")
            else:
                cursor.execute("INSERT INTO fort_sightings(fort_id, team, last_modified) VALUES (" + str(gym_id) + ", " + str(gym_team_id) + ", " + str(calendar.timegm(current_time.timetuple())) + ");")

            database.commit()

        except:
            database.rollback()
            if ( count > 1 ):
                await bot.say('Unsuccesful add to the map. There are multiple gyms with the word "' + str(raw_gym_name) + '" in it:\n' + str(gym_names) + '\nBe a little more specific.')
            elif ( count == 0 ):
                await bot.say('No gym with the word "' + str(raw_gym_name) + '" in it. Use the !list command to list all gyms available in the region.\n')
            else:
                await bot.say('Unsuccesful add to the map. !raid "*gym_name*" *pokemon_name* *raid_level* *minutes_left*\n')

@raid.error
async def handle_missing_raid_arg(ctx, error):
    await bot.say('Unsuccesful add to the map. Missing arguments. !raid  "*gym_name*"  *pokemon_name*  *raid_level*  *minutes_left*  *gym_team*\n')

@bot.command(pass_context=True)
async def list(ctx, raw_gym_name):
    if ctx and ctx.message.channel.id == str(bot_channel):
        database.ping(True)
        try:
            if raw_gym_name.isnumeric():
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE id LIKE '%" + str(raw_gym_name) + "%';")
            else:
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE name LIKE '%" + str(raw_gym_name) + "%';")
            data = cursor.fetchall()
            count = cursor.rowcount
            gym_names = ''
            for gym in data:
                gym_names += str(gym[0]) + ': ' + gym[1] + ' (' + str(gym[2]) + ', ' + str(gym[3]) + ')\n'
            await bot.say('There are ' + str(count) + ' gyms with the word(s) "' + str(raw_gym_name) + '" in it:\n' + str(gym_names))
            database.commit()
        except:
            database.rollback()
            await bot.say('No gym with the word "' + str(raw_gym_name) + '" in it OR too many to list. Try narrowing down your search.')

@list.error
async def handle_missing_arg(ctx, error):
    try:
        cursor.execute("SELECT id, name, lat, lon FROM forts;")
        data = cursor.fetchall()
        count = cursor.rowcount
        gym_names = ''
        for gym in data:
            gym_names += str(gym[0]) + ': ' + gym[1] + ' (' + str(gym[2]) + ', ' + str(gym[3]) + ')\n'
        database.commit()
        await bot.say('There are ' + str(count) + ' gyms in the region:\n' + str(gym_names))
    except:
        database.rollback()
        await bot.say('No gyms found OR too many to list.  Try narrowing down your search.')


@bot.command(pass_context=True)
async def map(ctx):
    if ctx:
        await bot.say('Visit ' + str(website) + ' to see our crowd-sourced Raids!')

@bot.command(pass_context=True)
async def deleteraid(ctx, fort_id):
    if ctx and ctx.message.channel.id == str(bot_channel):
        database.ping(True)
        current_time = datetime.datetime.utcnow()
        try:
            if fort_id.isnumeric():
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE id='" + str(fort_id) + "';")
                gym_data = cursor.fetchall()
                count = cursor.rowcount
                fort_id = gym_data[0][0]
                gym_name = gym_data[0][1]
                gym_lat = gym_data[0][2]
                gym_lon = gym_data[0][3]

                # Gym id is valid and returned 1 result
                if ( count == 1 ):
                    cursor.execute("SELECT fort_id, level, pokemon_id, time_battle, time_end FROM raids WHERE fort_id='" + str(fort_id) + "' AND time_end>'" + str(calendar.timegm(current_time.timetuple())) + "';")
                    raid_data = cursor.fetchall()
                    raid_count = cursor.rowcount

                    raid_fort_id = raid_data[0][0]
                    raid_level = raid_data[0][1]
                    raid_pokemon_id = raid_data[0][2]
                    raid_time_battle = raid_data[0][3]
                    raid_time_end = raid_data[0][4]

                    if ( raid_pokemon_id == 0 ):
                        raid_pokemon_name = 'Unknown (Egg)'
                    else:
                        raid_pokemon_name = pokejson[str(raid_pokemon_id)]

                    await bot.say('**Deleted the following raid**' +
                                  '\nGym: **' + str(fort_id) + ': ' + str(gym_name) + ' Gym**' +
                                  '\nLevel: **' + str(raid_level) + '**' +
                                  '\nPokemon: ** ' + str(raid_pokemon_name).capitalize() + '**' +
                                  '\nStart\Hatch Time: **' + str(time.strftime('%I:%M %p',  time.localtime(raid_time_battle))) + '**' +
                                  '\nEnd Time: **' + str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + '**')

                    cursor.execute("DELETE FROM raids WHERE fort_id='" + str(fort_id) + "' AND time_end>'" + str(calendar.timegm(current_time.timetuple())) + "';")
                    print(str(ctx.message.author.name) + ' deleted the Level ' + str(raid_level) + ' Raid at the ' + str(fort_id) + ': ' + str(gym_name) + ' Gym.')
                else:
                    await bot.say('Gym ID provided is not valid.')
            else:
                await bot.say('Enter the numeric ID of the gym where the raid is located.')

            database.commit()
        except:
            database.rollback()
            await bot.say('Raid at the **' + str(fort_id) + ': ' + str(gym_name) +  ' Gym** does not exist.')

@bot.command(pass_context=True)
async def activeraids(ctx):
    if ctx and ctx.message.channel.id == str(bot_channel):
        database.ping(True)
        current_time = datetime.datetime.utcnow()
        try:
            cursor.execute("SELECT f.id, f.name, r.level, r.pokemon_id, r.time_battle, r.time_end FROM forts f JOIN raids r ON f.id=r.fort_id WHERE r.time_end>'" + str(calendar.timegm(current_time.timetuple())) + "' ORDER BY r.level DESC, r.time_end;")
            raid_data = cursor.fetchall()
            raid_count = cursor.rowcount

            await bot.say('There are currently ' + str(raid_count) + ' active raids.')
            active_raids_l5 = ''
            active_raids_l4 = ''
            active_raids_l3 = ''
            active_raids_l2 = ''
            active_raids_l1 = ''
            for raid in raid_data:
                fort_id, gym_name, raid_level, raid_pokemon_id, raid_time_battle, raid_time_end = raid
                if ( raid_pokemon_id == 0 ):
                    raid_pokemon_name = 'Unknown (Egg)'
                else:
                    raid_pokemon_name = pokejson[str(raid_pokemon_id)]

                if ( raid_level == 5 ):
                    active_raids_l5 += str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + ' : ' + str(raid_pokemon_name) + ' : ' + str(gym_name) + ' Gym (' +  str(fort_id) + ')\n'
                elif ( raid_level == 4 ):
                    active_raids_l4 += str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + ' : ' + str(raid_pokemon_name) + ' : ' + str(gym_name) + ' Gym (' +  str(fort_id) + ')\n'
                elif ( raid_level == 3 ):
                    active_raids_l3 += str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + ' : ' + str(raid_pokemon_name) + ' : ' + str(gym_name) + ' Gym (' +  str(fort_id) + ')\n'
                elif ( raid_level == 2 ):
                    active_raids_l2 += str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + ' : ' + str(raid_pokemon_name) + ' : ' + str(gym_name) + ' Gym (' +  str(fort_id) + ')\n'
                else:
                    active_raids_l1 += str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + ' : ' + str(raid_pokemon_name) + ' : ' + str(gym_name) + ' Gym (' +  str(fort_id) + ')\n'

            raid_report = ''
            if ( active_raids_l5 != '' ):
                raid_report += '**LEVEL 5**\n' + active_raids_l5
            if ( active_raids_l4 != '' ):
                raid_report += '\n**LEVEL 4**\n' + active_raids_l4
            if ( active_raids_l3 != '' ):
                raid_report += '\n**LEVEL 3**\n' + active_raids_l3
            if ( active_raids_l2 != '' ):
                raid_report += '\n**LEVEL 2**\n' + active_raids_l2
            if ( active_raids_l1 != '' ):
                raid_report += '\n**LEVEL 1**\n' + active_raids_l1

            await bot.say('**END TIME : POKEMON : GYM**\n' + str(raid_report))

            database.commit()
        except:
            database.rollback()
            await bot.say('There are no active raids.')

@bot.command(pass_context=True)
async def updategymname(ctx, fort_id, new_gym_name):
    database.ping(True)
    if ctx and ctx.message.channel.id == str(bot_channel):
        try:
            cursor.execute("SELECT id, name FROM forts WHERE id='" + str(fort_id) + "';")
            gym_data = cursor.fetchall()
            gym_count = cursor.rowcount

            if ( gym_count == 1 ):
                fort_id, gym_name = gym_data[0]

                cursor.execute("UPDATE forts SET name='" + str(new_gym_name) + "' WHERE id='" + str(fort_id) + "';")
                cursor.execute("SELECT name FROM forts WHERE id='" + str(fort_id) + "';")
                updated_gym_data = cursor.fetchall()
                updated_gym_name = updated_gym_data[0][0]
                await bot.say('Changed the name of:\n__' + str(fort_id) + ': ' + str(gym_name) + '__\nto:\n**' + str(fort_id) + ': ' + str(updated_gym_name) + '**')
            else:
                await bot.say('There are multiple gyms with gym_id: ' + str(fort_id) + '.  Delete all of the duplicate gym_ids before proceeding.')
            database.commit()
        except:
            database.rollback()

@updategymname.error
async def handle_missing_fort_id(ctx, error):
    if ctx:
        try:
            await bot.say('Missing arugment(s).\n`!updategymname <gym_id> <new_gym_name>`')
        except:
            await bot.say('Exception reached.')


@bot.command(pass_context=True)
async def helpme(ctx):
    if ctx and ctx.message.channel.id == str(bot_channel):
        help_embed=discord.Embed(
            title='PoGoSD CSPM Help',
            content='**Mapping Raids:**\n'
                        'To add a raid to the live map, use the following command:\n'
                        '`!raid <gym_name or gym_id> <pokemon_name> <raid_level> <minutes remaining> <gym team>`\n'
                        'Example: `!raid "Fave Bird Mural" Lugia 5 45 Instinct`\n\n'
                        'Example: `!raid mural lugia 5 45 inst`\n\n'
                        'Example: `!raid 55 lugia 5 45 yel`\n\n'
                        '*To see raids that are crowdsourced, please make sure you tick the raids option in layers (top right)*\n\n'
                        '**List Gyms:**\n'
                        'This will help you search for gym names and ids:\n'
                        '`!list <search_string or number>`\n'
                        'Example: `!list 55`\n'
                        'Result: `55: Name of a Gym`\n\n'
                        '**Modify Gym Name**\n'
                        'Use this command to modify a gym name to help with identifying gyms with the same name, like Starbucks.  Use in conjunction with '
                        '!list to help you identify the gym_id.\n'
                        '`!updategymname 55 <new name of gym>`\n'
                        'Example: `!updategymname 55 "Starbucks inside Vons"`\n\n'
                        '**Delete Raids**\n'
                        'This will allow you to delete a raid by gym id\n'
                        '`!deleteraid <gym_id>`\n'
                        'Example: `!deleteraid 55`\n\n'
                        '**Show Active Raids**\n'
                        'This will allow you to list all active raids. Which is useful to identify a raid you may need to delete.\n'
                        '`!activeraids`',
            color=3447003
        )
        await bot.say(embed=help_embed)

bot.run(token)
