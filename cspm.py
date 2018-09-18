import MySQLdb
import discord
from discord.ext import commands
import asyncio
from pokemonlist import pokemon, pokejson, pokejson_by_name
from cspm_utils import find_pokemon_id, find_pokemon_name, get_team_id, get_team_name, get_team_color, get_egg_url, get_time, get_scoreboard, seconds_to_minutes, minutes_to_seconds
from config import admin_channel, admin_role_id, bot_channel, token, host, user, password, database, website, log_channel, instance_id, legendary_id, curfew, scoreboard_db, settings_db
import datetime
import calendar
import time
import threading
ADDED_EGG = 1
HATCHED_EGG = 2
ADDED_BOSS = 3
FULL_POINT = 1
PARTIAL_POINT = 0.5

bot = commands.Bot(command_prefix = '!') # Set prefix to !

database = MySQLdb.connect(host,user,password,database)

cursor = database.cursor()

scoreboard = get_scoreboard(scoreboard_db)

print('CSPM Started at ' + str(time.strftime('%I:%M %p on %m.%d.%y',  time.localtime(calendar.timegm(datetime.datetime.utcnow().timetuple())))) + ' for ' + str(instance_id) + '. Scoreboard set to: ' + str(scoreboard) + '. Default Settings Database set to: ' + str(settings_db))

async def incubate(ctx, gym_id, remaining_time):
    channel = discord.Object(id=bot_channel)
    current_time = datetime.datetime.utcnow()
    current_epoch_time = calendar.timegm(current_time.timetuple())
    sleep_time = remaining_time - current_epoch_time
    
    # Get default settings
    try:
        get_settings_query = "SELECT legendary_id, default_despawn_time FROM " + str(settings_db) + ";"
        cursor.execute(get_settings_query)
        default_settings = cursor.fetchall()
        default_settings_count = cursor.rowcount
        if ( default_settings_count ):
            default_legendary_id, default_despawn_time = default_settings[0]
            legendary_id = default_legendary_id

    except:
        print('Error. Something went wrong in incubate.')

    
    await bot.send_message(channel,'*Incubating Egg at Gym ID: ' + str(gym_id) + '. Will auto hatch in **' + str(sleep_time) + '** seconds.*')
    print('Auto-incubating Legendary egg at Gym ID: ' + str(gym_id) + '. Will auto hatch in ' + str(sleep_time) + ' seconds.')

    # Let's pause this thread until hatch time
    await asyncio.sleep(sleep_time)

    # Need to check if egg still exists before updating it and posting.  Otherwise, someone may have deleted it.
    cursor.execute("SELECT id FROM raids WHERE fort_id='" + str(gym_id)+ "' AND time_end>'" + str(current_epoch_time) + "';")
    raid_check = cursor.rowcount
    if ( raid_check == 1 ):
        cursor.execute("UPDATE raids SET pokemon_id='" + str(legendary_id) + "' WHERE fort_id='" + str(gym_id)+ "' AND time_end>'" + str(current_epoch_time) + "';")
        database.commit()

        cursor.execute("SELECT f.id, f.name, f.lat, f.lon, fs.team, r.level, r.pokemon_id, r.time_end FROM forts f JOIN raids r ON f.id=r.fort_id JOIN fort_sightings fs ON f.id = fs.fort_id WHERE f.id='" + str(gym_id) + "' AND r.time_end>'" + str(current_epoch_time) + "';")
        raid_data = cursor.fetchall()

        gym_id, gym_name, gym_lat, gym_lon, gym_team_id, raid_level, raid_pokemon_id, time_end = raid_data[0]
        await bot.send_message(channel,'Auto updated **Level ' + str(raid_level) + ' Egg to ' + str(pokejson[str(raid_pokemon_id)]) + ' Raid' + '**' +
                      '\nGym: **' + str(gym_id) + ': ' + str(gym_name) + ' Gym' + '**' +
                      '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(time_end))) + '**' +
                      '\nTeam: **' + str(get_team_name(gym_team_id)) + '**')
        print('Legendary egg at Gym ID: ' + str(gym_id) + ' hatched into ' + str(pokejson[str(raid_pokemon_id)]))

        raid_embed=discord.Embed(
            title='**Level ' + str(raid_level) + ' ' + str(pokejson[str(raid_pokemon_id)]) + ' Raid**',
            description='Gym: **' + str(gym_name) + ' Gym**' +
                        '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(time_end))) + '**' +
                        '\nTeam: **' + str(get_team_name(gym_team_id))+ '**' +
                        '\nReported by: __' + str(ctx.message.author.name) + '__' +
                        '\n\nhttps://www.google.com/maps?q=loc:' + str(gym_lat) + ',' + str(gym_lon),
            color=get_team_color(gym_team_id)
        )
        thumbnail_image_url = 'https://bitbucket.org/anzmap/sprites/raw/HEAD/' + str(raid_pokemon_id) + '.png'
        raid_embed.set_thumbnail(url=thumbnail_image_url)
        await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)
    else:
        print('Auto-hatch cancelled. Egg was not found, possibly deleted before hatch.')

async def score_it(ctx, gym_id, time_end_to_match, report_type):
    try:
        current_time = datetime.datetime.utcnow()
        scoreboard = get_scoreboard(scoreboard_db)
        score_eligibility_query = "SELECT s.id, s.raid_id, s.report_type FROM " + str(scoreboard) + " s JOIN raids r ON s.raid_id=r.id WHERE r.fort_id='" + str(gym_id) + "' AND s.report_type IS NOT NULL AND s.time_end>'" + str(calendar.timegm(current_time.timetuple())) + "';"
        #print("SELECT s.id, s.raid_id, s.report_type FROM " + str(scoreboard) + " s JOIN raids r ON s.raid_id=r.id WHERE r.fort_id='" + str(gym_id) + "' AND s.report_type IS NOT NULL AND s.time_end>'" + str(calendar.timegm(current_time.timetuple())) + "';")
        cursor.execute(score_eligibility_query)
        scoring_lines = cursor.fetchall()
        count = cursor.rowcount
        if (count):
            score_id, scored_raid_id, scored_report_type = scoring_lines[0]
      
        if ( count == 0 ):
            raid_query = "SELECT id, fort_id, level, time_end FROM raids WHERE fort_id='" + str(gym_id) + "' AND time_end='" + str(time_end_to_match) + "';"
            cursor.execute(raid_query)
            raid_data = cursor.fetchall()
            raid_id, fort_id, raid_level, raid_time_end = raid_data[0]
            
            insert_added_egg_query = "INSERT INTO " + str(scoreboard) + "(player_name, raid_id, raid_level, time_end, points, report_type) " + "VALUES ('" + str(ctx.message.author.name) + "','" + str(raid_id) + "','" + str(raid_level) + "','" + str(raid_time_end) + "','" + str(FULL_POINT) + "','" + str(ADDED_EGG) + "' );"
            cursor.execute(insert_added_egg_query)
 
            total_score_query = "SELECT SUM(points) AS total_points FROM " + str(scoreboard) + " WHERE player_name='" + str(ctx.message.author.name) + "';"
            cursor.execute(total_score_query)
            player_score = cursor.fetchall()
            player_total_score = player_score[0][0]
            
            notify_of_total_score = str(ctx.message.author.name) + " has " + str(player_total_score) + " points."
            
            notify_of_score = str(ctx.message.author.name) + " scored " + str(FULL_POINT) + " point."
            print(notify_of_score)
            await bot.send_message(discord.Object(id=bot_channel), "`\n" + notify_of_score + "\n" + notify_of_total_score + "`")
        elif ( (count == 1) and (scored_report_type == ADDED_EGG) ):
            raid_query = "SELECT id, fort_id, level, time_end FROM raids WHERE fort_id='" + str(gym_id) + "' AND time_end='" + str(time_end_to_match) + "';"
            cursor.execute(raid_query)
            raid_data = cursor.fetchall()
            raid_id, fort_id, raid_level, raid_time_end = raid_data[0]
            
            insert_hatched_egg_query = "INSERT INTO " + str(scoreboard) + "(player_name, raid_id, raid_level, time_end, points, report_type) " + "VALUES ('" + str(ctx.message.author.name) + "','" + str(raid_id) + "','" + str(raid_level) + "','" + str(raid_time_end) + "','" + str(FULL_POINT) + "','" + str(HATCHED_EGG) + "' );"
            cursor.execute(insert_hatched_egg_query)
            
            total_score_query = "SELECT SUM(points) AS total_points FROM " + str(scoreboard) + " WHERE player_name='" + str(ctx.message.author.name) + "';"
            cursor.execute(total_score_query)
            player_score = cursor.fetchall()
            player_total_score = player_score[0][0]
            
            notify_of_total_score = str(ctx.message.author.name) + " has " + str(player_total_score) + " points."
            
            notify_of_score = str(ctx.message.author.name) + " scored " + str(FULL_POINT) + " point."
            print(notify_of_score)
            await bot.send_message(discord.Object(id=bot_channel), "`\n" + notify_of_score + "\n" + notify_of_total_score + "`")
        else: # User maxed out attempts to score for this raid
            notify_of_nonscore = str(ctx.message.author.name) + " did not score points for this update."
            print(notify_of_nonscore)
            await bot.send_message(discord.Object(id=bot_channel), "`" + notify_of_nonscore + "`")
        database.commit()
    except:
        print('Error. Something went wrong in scoring.')
        database.rollback()

async def deduct_it(ctx, raid_id):
    try:
        scoreboard = get_scoreboard(scoreboard_db)
        query_scoreboard_for_raid = "SELECT id, player_name FROM " + str(scoreboard) + " WHERE raid_id='" + str(raid_id) + "' ORDER BY id DESC LIMIT 1;"
        cursor.execute(query_scoreboard_for_raid)
        raid_score_data = cursor.fetchall()
        raid_score_quantity = cursor.rowcount
        id, player_name_to_deduct = raid_score_data[0]
        
        if ( raid_score_quantity > 0 ):
            # Delete only the last raid that was scored
            delete_raid_from_scoreboard_query = "DELETE FROM " + str(scoreboard) + " WHERE raid_id='" + str(raid_id) + "' ORDER BY id DESC LIMIT 1;"
            cursor.execute(delete_raid_from_scoreboard_query)
            delete_count = cursor.rowcount
            database.commit()
            
            total_score_query = "SELECT SUM(points) AS total_points FROM " + str(scoreboard) + " WHERE player_name='" + str(player_name_to_deduct) + "';"
            cursor.execute(total_score_query)
            player_score = cursor.fetchall()
            player_total_score = player_score[0][0]

            notify_of_deduction = "Raid was deleted. " + str(delete_count) + " points were deducted from " + str(player_name_to_deduct) + ".\n" + str(player_name_to_deduct) + " now has " + str(player_total_score) + " points."
            print(notify_of_deduction)
            await bot.send_message(discord.Object(id=bot_channel), "`" + notify_of_deduction + "`")
        else:
            raise Exception('Raid was deleted but was never scored so no points were deducted.')
        database.commit()

    except Exception as e:
        message = e.args[0]
        await bot.send_message(discord.Object(id=bot_channel), message)
        print(message)
    except:
        database.rollback()

#raid function
@bot.command(pass_context=True)
async def raid(ctx, raw_gym_name, raw_pokemon_name, raw_raid_level, raw_time_remaining, raw_team):
    if ctx and ctx.message.channel.id == str(bot_channel):
        pokemon_name = str(raw_pokemon_name).capitalize()
        pokemon_id = find_pokemon_id(pokemon_name)
        remaining_time = get_time(int(raw_time_remaining))
        current_time = datetime.datetime.utcnow()
        current_hour = time.strftime('%H%M',  time.localtime(calendar.timegm(current_time.timetuple())))
        gym_team_id = get_team_id(raw_team)
        database.ping(True)

        try:
            if ( (int(raw_raid_level) < 1) or (int(raw_raid_level) > 5) ):
                raise Exception('Invalid raid level entered. Enter value between 1-5.')
            if ( (int(raw_time_remaining) < 1) or (int(raw_time_remaining) >= 90) ):
                raise Exception('Invalid time entered. Enter value between 1-90.')
            if ( curfew == 'true' ):
                if ( (int(current_hour) >= 1930) or (int(current_hour) <= 500) ):
                    raise Exception('Raid report is outside of the valid raid times. Raids can be reported between 5am - 7:30pm daily.')

            if raw_gym_name.isnumeric():
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE id LIKE '" + str(raw_gym_name) + "';")
            else:
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE name LIKE '%" + str(raw_gym_name) + "%';")
            gym_data = cursor.fetchall()
            count = cursor.rowcount
            raid_count = 0
            gym_names = ''
            for gym in gym_data:
                gym_names += str(gym[0]) + ': ' + gym[1] + ' (' + str(gym[2]) + ', ' + str(gym[3]) + ')\n'
                    
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
            elif ( count > 1 ):
                raise Exception('Unsuccesful add to the map. There are multiple gyms with the word "' + str(raw_gym_name) + '" in it:\n' + str(gym_names) + '\nBe a little more specific.')
            elif ( count == 0 ):
                raise Exception('No gym with the word "' + str(raw_gym_name) + '" in it. Use the !list command to list gyms available in the region.\n')
            else:
                raise Exception('Unsuccesful add to the map. !raid "*gym_name*" *pokemon_name* *raid_level* *minutes_left*\n')

            if ( pokemon_name == "Egg" ):
                # Get default settings
                try:
                    get_settings_query = "SELECT legendary_id, default_despawn_time FROM " + str(settings_db) + ";"
                    cursor.execute(get_settings_query)
                    default_settings = cursor.fetchall()
                    default_settings_count = cursor.rowcount
                    if ( default_settings_count ):
                        default_legendary_id, default_despawn_time = default_settings[0]
                        est_end_time = remaining_time + default_despawn_time
                    else:
                        est_end_time = remaining_time + 2700
                except:
                    print('Error. Something went wrong in raid.')
                
                if (raid_count):
                    cursor.execute("UPDATE raids SET level='" + str(raw_raid_level) + "', time_battle='" + str(remaining_time) + "', time_end='" + str(est_end_time) + "' WHERE id='" + str(raid_id)+ "';")
                    await bot.say('Updated **Level ' + str(raw_raid_level) + ' ' + str(pokemon_name) + '**' +
                                  '\nGym: **' + str(gym_id) + ': ' + str(gym_name) + ' Gym' + '**' +
                                  '\nHatches: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                  '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(est_end_time))) + '**' +
                                  '\nTeam: **' + str(get_team_name(gym_team_id)) + '**' +
                                  '\n\n`No points were scored because raid was already reported.`')
                else:
                    # Setup task to automatically hatch Legendary egg
                    if ( raw_raid_level == '5' ):
                        bot.loop.create_task(incubate(ctx, gym_id, remaining_time))
                    
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
                                  '\nTime Left Until Hatch: **' + str(raw_time_remaining) + ' minutes**' +
                                  '\nTeam: **' + str(get_team_name(gym_team_id)) + '**')
                    raid_embed=discord.Embed(
                        title='**Level ' + str(raw_raid_level) + ' Egg**',
                        description='Gym: **' + str(gym_name) + ' Gym**' +
                                    '\nHatches: **' + str(time.strftime('%I:%M %p',  time.localtime(remaining_time))) + '**' +
                                    '\nRaid Ends: **' + str(time.strftime('%I:%M %p',  time.localtime(est_end_time))) + '**' +
                                    '\nTeam: **' + str(get_team_name(gym_team_id))+ '**' +
                                    '\nReported by: __' + str(ctx.message.author.name) + '__' +
                                    '\n\nhttps://www.google.com/maps?q=loc:' + str(gym_data[0][2]) + ',' + str(gym_data[0][3]),
                        color=get_team_color(gym_team_id)
                    )
                    thumbnail_image_url = get_egg_url(raw_raid_level)
                    raid_embed.set_thumbnail(url=thumbnail_image_url)
                    await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)
                    
                    print(str(ctx.message.author.name) + ' reported a ' + str(pokemon_name) + ' at ' + str(gym_id) +': ' + str(gym_name) + ' gym with ' + str(raw_time_remaining) + ' minutes left.')
                    bot.loop.create_task(score_it(ctx, gym_id, est_end_time, ADDED_EGG))
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
                        color=get_team_color(gym_team_id)
                    )
                    thumbnail_image_url = 'https://bitbucket.org/anzmap/sprites/raw/HEAD/' + str(pokemon_id) + '.png'
                    raid_embed.set_thumbnail(url=thumbnail_image_url)
                    await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)

                    print(str(ctx.message.author.name) + ' updated the ' + str(raw_raid_level) + ' Egg to ' + str(pokemon_name) + ' Raid at ' + str(gym_name) + ' gym (' + str(get_team_name(gym_team_id)) + ') with ' + str(raw_time_remaining) + ' minutes left.')

                    bot.loop.create_task(score_it(ctx, gym_id, remaining_time, HATCHED_EGG))
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
                        color=get_team_color(gym_team_id)
                    )
                    thumbnail_image_url = 'https://bitbucket.org/anzmap/sprites/raw/HEAD/' + str(pokemon_id) + '.png'
                    raid_embed.set_thumbnail(url=thumbnail_image_url)
                    await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)
                    print(str(ctx.message.author.name) + ' reported a ' + str(pokemon_name) + ' raid at ' + str(gym_name) + ' gym (' + str(get_team_name(gym_team_id)) + ') with ' + str(raw_time_remaining) + ' minutes left.')
                    
                    bot.loop.create_task(score_it(ctx, gym_id, remaining_time, ADDED_BOSS))
            # Check if fort_id exists in fort_sightings.  If so update the entry, otherwise enter as a new entry.
            cursor.execute("SELECT id, fort_id, team FROM fort_sightings WHERE fort_id='" + str(gym_id) + "';")
            fs_count = cursor.rowcount
            if (fs_count):
                fort_sightings_query = "UPDATE fort_sightings SET team='" + str(gym_team_id) + "', guard_pokemon_id='" + str(pokemon_id) + "' WHERE fort_id='" + str(gym_id) + "';"
                cursor.execute(fort_sightings_query)
            else:
                fort_sightings_query = "INSERT INTO fort_sightings(fort_id, team, last_modified, guard_pokemon_id) VALUES (" + str(gym_id) + ", " + str(gym_team_id) + ", " + str(calendar.timegm(current_time.timetuple())) + ", " + str(pokemon_id) + ");"
                cursor.execute(fort_sightings_query)
            database.commit()

        except Exception as e:
            message = e.args[0]
            await bot.say(message)
            print(message)

        except:
            database.rollback()

@raid.error
async def handle_missing_raid_arg(ctx, error):
    await bot.say('Unsuccesful add to the map. Missing arguments. !raid  "*gym_name*"  *pokemon_name*  *raid_level*  *minutes_left*  *gym_team*\n')

@bot.command(pass_context=True)
async def list(ctx, raw_gym_name):
  
    if ctx and ( (ctx.message.channel.id == str(bot_channel)) or ((ctx.message.channel.id == str(admin_channel)))):
        database.ping(True)
        try:
            if raw_gym_name.isnumeric():
                cursor.execute("SELECT id, name, lat, lon FROM forts WHERE id LIKE '" + str(raw_gym_name) + "';")
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
        try:
            database.ping(True)
            scoreboard = get_scoreboard(scoreboard_db)
            current_time = datetime.datetime.utcnow()
            valid_user_query = "SELECT s.player_name FROM raids r JOIN " + str(scoreboard) + " s ON r.id = s.raid_id WHERE r.fort_id='" + str(fort_id) + "' AND r.time_end>'" + str(calendar.timegm(current_time.timetuple())) + "' AND s.player_name='" + str(ctx.message.author.name) +  "';"
            print(str(valid_user_query))
            cursor.execute(valid_user_query)
            valid_user_count = cursor.rowcount
            print(str(valid_user_count))
            # Check if command is coming from original raid reporter or an admin
            if ( (valid_user_count == 0) and (admin_role_id not in [role.id for role in ctx.message.author.roles]) ):
                raise Exception('Raid can only be deleted by original reporter or an Admin.')

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
                    cursor.execute("SELECT r.id, r.fort_id, r.level, r.pokemon_id, r.time_battle, r.time_end, fs.team FROM raids r JOIN fort_sightings fs ON r.fort_id = fs.fort_id WHERE r.fort_id='" + str(fort_id) + "' AND r.time_end>'" + str(calendar.timegm(current_time.timetuple())) + "';")
                    raid_data = cursor.fetchall()
                    raid_count = cursor.rowcount

                    raid_id, raid_fort_id, raid_level, raid_pokemon_id, raid_time_battle, raid_time_end, raid_gym_team = raid_data[0]

                    if ( raid_pokemon_id == 0 ):
                        raid_pokemon_name = 'Unknown (Egg)'
                        thumbnail_image_url = get_egg_url(raid_level)
                    else:
                        raid_pokemon_name = pokejson[str(raid_pokemon_id)]
                        thumbnail_image_url = 'https://bitbucket.org/anzmap/sprites/raw/HEAD/' + str(raid_pokemon_id) + '.png'

                    await bot.say('**Deleted the following raid**' +
                                  '\nGym: **' + str(fort_id) + ': ' + str(gym_name) + ' Gym**' +
                                  '\nLevel: **' + str(raid_level) + '**' +
                                  '\nPokemon: ** ' + str(raid_pokemon_name).capitalize() + '**' +
                                  '\nStart\Hatch Time: **' + str(time.strftime('%I:%M %p',  time.localtime(raid_time_battle))) + '**' +
                                  '\nEnd Time: **' + str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + '**')
                    delete_raid_query = "DELETE FROM raids WHERE fort_id='" + str(fort_id) + "' AND time_end>'" + str(calendar.timegm(current_time.timetuple())) + "';"
                    cursor.execute(delete_raid_query)

                    # Deduct the points
                    bot.loop.create_task(deduct_it(ctx, raid_id))

                    raid_embed=discord.Embed(
                        title='~~Level ' + str(raid_level) + ' ' + str(raid_pokemon_name).capitalize() + ' Raid~~ **RAID DELETED**',
                        description='Gym: ~~' + str(gym_name) + ' Gym~~' +
                                    '\nRaid Ends: ~~' + str(time.strftime('%I:%M %p',  time.localtime(raid_time_end))) + '~~' +
                                    '\nTeam: ~~' + str(get_team_name(raid_gym_team))+ '~~' +
                                    '\nDeleted by: __' + str(ctx.message.author.name) + '__',
                        color=get_team_color(raid_gym_team)
                    )
                    raid_embed.set_thumbnail(url=thumbnail_image_url)
                    await bot.send_message(discord.Object(id=log_channel), embed=raid_embed)

                    print(str(ctx.message.author.name) + ' deleted the Level ' + str(raid_level) + ' Raid at the ' + str(fort_id) + ': ' + str(gym_name) + ' Gym.')
                else:
                    raise Exception('Gym ID provided is not valid.')
        
            else:
                raise Exception('Enter the numeric ID of the gym where the raid is located.')

            database.commit()
        except Exception as e:
            message = e.args[0]
            await bot.send_message(discord.Object(id=bot_channel), message)
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

            if ( raid_report != '' ):
                await bot.say('**END TIME : POKEMON : GYM**\n' + str(raid_report))

            database.commit()
        except:
            database.rollback()
            await bot.say('There are no active raids.')

@bot.command(pass_context=True)
async def updategymname(ctx, fort_id, new_gym_name):
    if ( admin_channel == 'disabled'):
        await bot.say('The !updategymname command is disabled')
        pass
    else:
        database.ping(True)
        if ctx and ctx.message.channel.id == str(admin_channel):
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
async def scoreboard(ctx):
    if ctx and ctx.message.channel.id == str(bot_channel):
        try:
            scoreboard = get_scoreboard(scoreboard_db)
            scoreboard_query = "SELECT player_name, SUM(points) AS total_points FROM " + str(scoreboard) + " GROUP BY player_name ORDER BY total_points DESC LIMIT 100;"
            cursor.execute(scoreboard_query)
            scoreboard_data = cursor.fetchall()
            count = cursor.rowcount
          
            if ( count == 0 ):
                raise Exception('The scoreboard is currently empty.')
            
            leaderboard = ''
            position = 1
            for player in scoreboard_data:
                player_name, total_points = player
                leaderboard += str(position) + '. ' + str(player_name) + ': ' + str(total_points) + '\n'
                position += 1

            if ( leaderboard != '' ):
                await bot.send_message(discord.Object(id=bot_channel),str(leaderboard))
            
            database.commit()

        except Exception as e:
            message = e.args[0]
            await bot.send_message(discord.Object(id=bot_channel), message)
            
        except:
            database.rollback()

@bot.command(pass_context=True)
async def gymscores(ctx):
    if ctx and ctx.message.channel.id == str(bot_channel):

        try:
            scoreboard = get_scoreboard(scoreboard_db)
            gymscores_query = "SELECT f.id, f.name, COUNT(s.player_name) AS Count FROM (forts f INNER JOIN raids r ON f.id = r.fort_id) INNER JOIN " + str(scoreboard) + " s ON r.id = s.raid_id GROUP BY f.id ORDER BY Count DESC LIMIT 25;"
            cursor.execute(gymscores_query)
            gymscores_data = cursor.fetchall()
            count = cursor.rowcount
            
            if ( count == 0 ):
                raise Exception('The gym scoreboard is currently empty.')
            
            gymboard = ''
            for gym in gymscores_data:
                gym_id, gym_name, total = gym;
                gymboard += str(gym_id) + '. ' + str(gym_name) + ': ' + str(total) + '\n'
            
            if ( gymboard != '' ):
                gymboard_header = '**GYM ID. GYM NAME: NUMBER OF REPORTS**\n'
                gymboard = gymboard_header + gymboard
                await bot.send_message(discord.Object(id=bot_channel),str(gymboard))
            database.commit()
        
        except Exception as e:
            message = e.args[0]
            await bot.send_message(discord.Object(id=bot_channel), message)
        except:
            database.rollback()


@bot.command(pass_context=True)
async def clearscoreboard(ctx):
    if ( admin_channel == 'disabled'):
        await bot.say('The !clearscoreboard command is disabled for this channel.')
        pass
    else:
        if ctx and ctx.message.channel.id == str(admin_channel):
            try:
                scoreboard = get_scoreboard(scoreboard_db)
                clear_scoreboard_query = "DELETE FROM " + str(scoreboard) + ";"
                cursor.execute(clear_scoreboard_query)
                await bot.say('The scoreboard has been cleared!')
                database.commit()
            except:
                database.rollback()

@bot.command(pass_context=True)
async def deletegym(ctx, fort_id):
    if ( admin_channel == 'disabled'):
        await bot.say('The !deletegym command is disabled')
        pass
    else:
        database.ping(True)
        
        if ctx and ctx.message.channel.id == str(admin_channel):
            try:
                get_gym_name_query = "SELECT name FROM forts WHERE id='" + str(fort_id) + "';"
                cursor.execute(get_gym_name_query)
                gym_data = cursor.fetchall()
                gym_count = cursor.rowcount
                database.commit()
                
                if (gym_count):
                    gym_name = gym_data[0][0]
                    cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
                    database.commit()

                    await bot.say('Deleting ' + str(gym_count) + ' gym.')
                    delete_gym_query = "DELETE FROM forts WHERE id='" + str(fort_id) + "';"
                    cursor.execute(delete_gym_query)
                    database.commit()
                    await bot.say('Successfully deleted gym: ' + str(fort_id) + '. ' + str(gym_name) + '.')


                    cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
                    database.commit()
                else:
                    await bot.say('Failed to deleted gym.  Gym ' + str(fort_id) + ' was not found.')
            except:
                database.rollback()

@bot.command(pass_context=True)
async def addgym(ctx, name, lat, lon):
    if ( admin_channel == 'disabled'):
        await bot.say('The !addgym command is disabled')
        pass
    else:
        database.ping(True)
        
        if ctx and ctx.message.channel.id == str(admin_channel):
            try:
                add_gym_query = "INSERT INTO forts (name, lat, lon) VALUES ('" + str(name) + "','" + str(lat) + "','" + str(lon) + "');"
                await bot.say('Adding **' + str(name) + '** gym. With coordinates (' + str(lat) + ', ' + str(lon) + ')')
                cursor.execute(add_gym_query)
                database.commit()
            
                verify_gym_query = "SELECT id, name, lat, lon FROM forts WHERE name='" + str(name) + "';"
                cursor.execute(verify_gym_query)
                gym_entry = cursor.fetchall()
                gym_count = cursor.rowcount
                
                if (gym_count):
                    gym_id, gym_name, gym_lat, gym_lon = gym_entry[0]
                    add_external_id_query = "UPDATE forts SET external_id='1000000000000000000000000000" + str(gym_id) + ".16' WHERE id='" + str(gym_id) + "';"
                    print('add_external_id_query = ' + str(add_external_id_query))
                    await bot.say('add_external_id_query = ' + str(add_external_id_query))
                    cursor.execute(add_external_id_query)
                    database.commit()
                    await bot.say('Successfully added **' + str(gym_id) + '. ' + str(gym_name) + ' Gym (' + str(gym_lat) + ', ' + str(gym_lon) + ')**')
                else:
                    await bot.say('Failed to add **' + str(name) + ' Gym.**')
                database.commit()
            except:
                database.rollback()

@bot.command(pass_context=True)
async def setlegendary(ctx, raw_pokemon_name):
    if ( admin_channel == 'disabled'):
        await bot.say('The !setlegendaryid command is disabled')
        pass
    else:
        database.ping(True)
        pokemon_name = str(raw_pokemon_name).capitalize()
        pokemon_id = find_pokemon_id(pokemon_name)
        
        if ctx and ctx.message.channel.id == str(admin_channel):
            try:
                get_settings_query = "SELECT legendary_id, default_despawn_time FROM " + str(settings_db) + ";"
                cursor.execute(get_settings_query)
                default_settings = cursor.fetchall()
                default_settings_count = cursor.rowcount

                if ( default_settings_count ):
                    default_legendary_id, default_despawn_time = default_settings[0]
                    time_in_minutes = seconds_to_minutes(default_despawn_time)
                    pokemon_name = find_pokemon_name(default_legendary_id)
                    
                    await bot.say('Legendary ID was set to: **' + str(default_legendary_id) + '  (' + str(pokemon_name) + ')**\nDefault Despawn Time is set to: **' + str(time_in_minutes) + ' minutes (' + str(default_despawn_time) + ' seconds)**')
                    set_legendary_id_query = "UPDATE " + str(settings_db) + " SET legendary_id='" + str(pokemon_id) + "';"
                else:
                    await bot.say('Default settings were not configured.')
                    set_legendary_id_query = "INSERT INTO " + str(settings_db) + " (legendary_id) VALUES ('" + str(pokemon_id) + "');"
                database.commit()
            
            
                cursor.execute(set_legendary_id_query)
                database.commit()
            
                cursor.execute(get_settings_query)
                updated_default_settings = cursor.fetchall()
                default_legendary_id, default_despawn_time = updated_default_settings[0]
                time_in_minutes = seconds_to_minutes(default_despawn_time)
                pokemon_name = find_pokemon_name(default_legendary_id)
                
                await bot.say('Legendary ID **UPDATED** to: **' + str(default_legendary_id) + '  (' + str(pokemon_name) + ')**\nDefault Despawn Time is set to: **' + str(time_in_minutes) + ' minutes (' + str(default_despawn_time) + ' seconds)**')
                database.commit()
            except:
                database.rollback()

@bot.command(pass_context=True)
async def setdespawn(ctx, minutes_input):
    if ( admin_channel == 'disabled'):
        await bot.say('The !setdespawn command is disabled')
        pass
    else:
        database.ping(True)
        
        if ctx and ctx.message.channel.id == str(admin_channel):
            try:
                get_settings_query = "SELECT legendary_id, default_despawn_time FROM " + str(settings_db) + ";"
                cursor.execute(get_settings_query)
                default_settings = cursor.fetchall()
                default_settings_count = cursor.rowcount

                if ( default_settings_count ):
                    default_legendary_id, default_despawn_time = default_settings[0]
                    time_in_minutes = seconds_to_minutes(default_despawn_time)
                    pokemon_name = find_pokemon_name(default_legendary_id)
                    
                    await bot.say('Legendary ID is set to: **' + str(default_legendary_id) + ' (' + str(pokemon_name) + ')**\nDefault Despawn Time was set to: **' + str(time_in_minutes) + ' minutes (' + str(default_despawn_time) + ' seconds)**')
                    
                    new_time_seconds = minutes_to_seconds(minutes_input)
                    set_legendary_id_query = "UPDATE " + str(settings_db) + " SET default_despawn_time='" + str(new_time_seconds) + "';"
                else:
                    await bot.say('Default settings were not configured.')
                    
                    new_time_seconds = minutes_to_seconds(minutes_input)
                    set_legendary_id_query = "INSERT INTO " + str(settings_db) + " (default_despawn_time) VALUES ('" + str(new_time_seconds) + "');"
                database.commit()
            
            
                cursor.execute(set_legendary_id_query)
                database.commit()
            
                cursor.execute(get_settings_query)
                updated_default_settings = cursor.fetchall()
                default_legendary_id, default_despawn_time = updated_default_settings[0]
                time_in_minutes = seconds_to_minutes(default_despawn_time)
                pokemon_name = find_pokemon_name(default_legendary_id)
                
                await bot.say('Legendary ID is set to: **' + str(default_legendary_id) + '  (' + str(pokemon_name) + ')**\nDefault Despawn Time **UPDATED** to: **' + str(time_in_minutes) + ' minutes (' + str(default_despawn_time) + ' seconds)**')
                database.commit()
            except:
                database.rollback()

@bot.command(pass_context=True)
async def defaultsettings(ctx):
    if ( admin_channel == 'disabled'):
        await bot.say('The !defaultsettings command is disabled')
        pass
    else:
        database.ping(True)
        
        if ctx and ctx.message.channel.id == str(admin_channel):
            try:
                get_settings_query = "SELECT legendary_id, default_despawn_time FROM " + str(settings_db) + ";"
                cursor.execute(get_settings_query)
                default_settings = cursor.fetchall()
                default_settings_count = cursor.rowcount

                if ( default_settings_count ):
                    default_legendary_id, default_despawn_time = default_settings[0]
                    despawn_seconds = default_despawn_time
                    despawn_minutes = seconds_to_minutes(default_despawn_time)
                    pokemon_name = find_pokemon_name(default_legendary_id)
                    await bot.say('Legendary ID is set to: **' + str(default_legendary_id) + ' (' + str(pokemon_name) + ')**\nDefault Despawn Time is set to: **' + str(despawn_minutes) + ' minutes (' + str(despawn_seconds) + ' seconds)**')
                else:
                    await bot.say('Default settings were not configured.')
                database.commit()
            except:
                database.rollback()

@bot.command(pass_context=True)
async def helpme(ctx):
    if ctx and (ctx.message.channel.id == str(bot_channel) or ctx.message.channel.id == str(admin_channel)):
        help_embed1=discord.Embed(
            title='PoGoSD CSPM Help - Typical Commands',
            description='**Mapping Raids:**\n'
                    'To add a raid to the live map, use the following command:\n'
                    '`!raid <gym_name or gym_id> <pokemon_name> <raid_level> <minutes remaining> <gym team>`\n'
                    'Example: `!raid "Fave Bird Mural" Lugia 5 45 Instinct`\n'
                    'Example: `!raid mural lugia 5 45 inst`\n'
                    'Example: `!raid 55 lugia 5 45 yel`\n\n'
                    '*Legendary Eggs will automatically hatch if not manually updated.*\n\n'
                    '**List Gyms:**\n'
                    'This will help you search for gym names and ids:\n'
                    '`!list <search_string or number>`\n'
                    'Example: `!list 55`\n'
                    'Result: `55: Name of a Gym`\n\n'
                    '**Delete Raids**\n'
                    'This will allow you to delete a raid by gym id\n'
                    '`!deleteraid <gym_id>`\n'
                    'Example: `!deleteraid 55`\n\n'
                    '**Show Active Raids**\n'
                    'This will allow you to list all active raids. Which is useful to identify a raid you may need to delete.\n'
                    '`!activeraids`',
            color=3447003
        )
        help_embed2=discord.Embed(
            title='PoGoSD CSPM Help - Administrative Commands',
            description='**Modify Gym Name** (*only available on an admin channel*)\n'
                    'Use this command to modify a gym name to help with identifying gyms with the same name, like Starbucks.  Use in conjunction with '
                    '!list to help you identify the gym_id.\n'
                    '`!updategymname 55 <new name of gym>`\n'
                    'Example: `!updategymname 55 "Starbucks inside Vons`\n\n'
                    '**Clear Scoreboard** (*only available on an admin channel*)\n'
                    'Use this command to clear the scoreboard.\n'
                    'Example: `!clearscoreboard`\n\n'
                    '**Delete Gym** (*only available on an admin channel*)\n'
                    '!deletegym <gym_id>\n'
                    'Example: `!deletegym 55`\n\n'
                    '**Add Gym** (*only available on an admin channel*)\n'
                    'Use this command to add a new gym given the <gym_name> and coordinates <lat> <lon>\n'
                    'Example: `!addgym "Another Utility Box" 12.345 -456.123`\n'
                    'Example: `!addgym "Lend A Hand" 32.917845 -117.120401`\n'
                    'Example: `!addgym "Ladies Utility Box" 32.920107 -117.120327`\n\n'
                    '**Set Legendary Boss Name** (*only available on an admin channel*)\n'
                    'Use this command to set the default Legendary Boss for autohatch\n'
                    'Example: `!setlegendaryid Lugia`\n'
                    'Example: `!setlegendaryid Regice`\n\n'
                    '**Set Default Despawn Time** (*only available on an admin channel*)\n'
                    'Use this command to set the default despawn time (in minutes) for a Legendary Boss during autohatch\n'
                    'Example for 45 minutes: `!setdespawn 45`\n'
                    'Example for 15 minutes: `!setdespawn 15`\n\n'
                    '**Show Default Settings** (*only available on an admin channel*)\n'
                    'Use this command to show the default settings for a Legendary Boss during autohatch\n'
                    'Example: `!defaultsettings`',
            color=3447003
        )
        await bot.say(embed=help_embed1)
        if ( admin_channel == 'disabled'):
            pass
        else:
            if (ctx.message.channel.id == str(admin_channel)):
                await bot.say(embed=help_embed2)
            else:
                pass

bot.run(token)
