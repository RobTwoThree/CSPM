bot_channel = '12345' #limit users to using the bot in this channel, right click and copy ID.
token= 'XXXX12345' #discord bot token (NOT bot ID)
website = 'http://mapnamehere.com' #URL to map if you want the .map function to work, simply gives the users the website
log_channel = '01234' #Add a log channel, copy the ID here, give this bot access to the channel.
admin_channel = '0123456' #Add an admin channel for updategymname (admin only) and list (admin or bot) commands.  To disable use admin_channel = 'disabled'

#####DATABASE, limited to MySQL and MariaDB#####
host = 'localhost'  #host
user = 'username'  #database user
password = 'password'  #database password
database = 'database_name'  #database name

########Custom Fields#########
instance_id = 'instance_name'
legendary_id = '381'
curfew = 'true'  #set to true to disable posts from 7:30pm to 5:00am
admin_role_id = 'disabled' #set to admin_role_id to allow overrides of various commands like !deleteraid
scoreboard_db = 'disabled' #specify if multiple scoreboards are used with a single fort database
