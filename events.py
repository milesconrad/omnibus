import discord
from datetime import datetime
from time import sleep
from ast import literal_eval as str_to_list
from builtins import bot, cursor, connection

# creates a table for the joined guild in omnibus.db
@bot.event
async def on_guild_join(guild):
    role = discord.utils.get(guild.roles, name="member")
    if not role:
        await guild.system_channel.send('''Sorry, in order to use this bot you need to have a 
            member role in your server! You will also need to give
            the member role full privileges, as the greeting message 
            tells users they have them.''')
        await guild.leave()
        return

    cursor.execute(f'''create table "{str(guild.id)}"(
        member text not null,
        rolelist text
        )''')

    # iterates through every role of every user and adds it to the table
    for member in guild.members:
        if not member.bot:
            stored_roles = []
            for role in member.roles:
                if role.name != "member" and role.name != "@everyone":
                    stored_roles.append(role.id)

            if stored_roles:
                cursor.execute(f'insert into "{str(guild.id)}" values ("{str(member.id)}", "{str(stored_roles)}")')
            else:
                cursor.execute(f'insert into "{str(guild.id)}" (member) values ("{member.id}")')

    connection.commit()

@bot.event
async def on_guild_remove(guild):
    try:
        cursor.execute(f'select * from "{str(guild.id)}"')
    except:
        return
    cursor.execute(f'drop table "{str(guild.id)}"')
    connection.commit()

# checks if the new member has joined before, and if so gives back their roles
@bot.event
async def on_member_join(member):
    if not member.bot:
        role = discord.utils.get(member.guild.roles, name="member")
        await member.add_roles(role)
        
        cursor.execute(f'select * from "{str(member.guild.id)}" where member="{member.id}"')
        stored_roles = cursor.fetchone()

        # if there is no slot for the user, create one and welcome them
        if not stored_roles:
            cursor.execute(f'insert into "{str(member.guild.id)}" (member) values ("{member.id}")')
            sleep(1)
            await member.guild.system_channel.send(f"Welcome <@{member.id}>, every user has admin, so go ahead and give yourself the roles you'd like.")

        elif stored_roles[1]:
            # index 0 of stored_roles is the member id, index 1 is the list of roles
            stored_roles = str_to_list(stored_roles[1])
            for role_id in stored_roles:
                try:
                    role = discord.utils.get(member.guild.roles, id=role_id)
                    await member.add_roles(role)
                except:
                    stored_roles.remove(role_id)
                    cursor.execute(f'update "{str(member.guild.id)}" set rolelist="{str(stored_roles)}" where member="{member.id}"')

    else:
        role = discord.utils.get(member.guild.roles, name="bots")
        await member.add_roles(role)

    connection.commit()

@bot.event
async def on_member_update(before, after):
    if not before.bot:
        joined_at = before.joined_at.timestamp()
        now = datetime.utcnow().timestamp()
        new_roles = list(set(after.roles) - set(before.roles))
        removed_roles = list(set(before.roles) - set(after.roles))
    
        # checks if the change was a change in roles, and if the member has been
        # joined for longer than 3 seconds (to ignore on_member_join actions)
        if (new_roles or removed_roles) and now - joined_at > 3.0:
            cursor.execute(f'select * from "{str(before.guild.id)}" where member="{str(before.id)}"')
            # index 0 of stored_roles is the member id, index 1 is the list of roles
            stored_roles = cursor.fetchone()
            if stored_roles[1]:
                stored_roles = str_to_list(stored_roles[1])
            else:
                stored_roles = []

            if new_roles and new_roles[0].name != "member":
                stored_roles.append(new_roles[0].id)
                cursor.execute(f'update "{str(before.guild.id)}" set rolelist="{str(stored_roles)}" where member="{str(before.id)}"')
            elif removed_roles and removed_roles[0].name != "member":
                stored_roles.remove(removed_roles[0].id)
                cursor.execute(f'update "{str(before.guild.id)}" set rolelist="{str(stored_roles)}" where member="{str(before.id)}"')
                    
    connection.commit()

@bot.event
async def on_member_ban(guild, user):
    if not user.bot:
        cursor.execute(f'delete from "{str(guild.id)}" where member="{str(user.id)}"')
        connection.commit()