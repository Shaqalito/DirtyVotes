import os
import json
import datetime
from discord_components import DiscordComponents
from discord_components import SelectOption, Select
from discord import Embed
from discord_slash import SlashCommand
from discord.ext import commands, tasks
from keep_alive import keep_alive
import discord
from system import Guild_Manager, GuildErrors


# Clear shortcut function
def clear():
    os.system("clear")


"""####################### System Variables #################################"""
intents = discord.Intents().all()  # Creating the bot intents
client = commands.Bot(command_prefix=".", intents=intents)  # Initiating the bot reffered to as client
slash = SlashCommand(client, sync_commands=True)  # Initiating slash command for our client (bot object is reffered to as client)


# ON READY
@client.event
async def on_ready():
    DiscordComponents(client)  # Initiate Discord Components
    clear()  # Clear Console
    get_poll.start()  # Start both tasks get_poll and update_db_task
    print(f"Logged in as {client.user}")
    print(f"Ping (ms): {round(client.latency * 1000)}")


guilds_ids = Guild_Manager.get_all_guilds()  # Guild id for convenience
bot_color = 0x24C29C  # The hex color code of the bot (WILL BE CHANGED TO BE DYNAMICALLY SETABLE WITH A SLASH COMMAND)


# CHECK FOR STAFF ROLES
def check_for_auth_roles(user):
    auth_roles = Guild_Manager(user.guild).get_auth_roles()
    if auth_roles == []:
        return True
    if any(role in user.roles for role in auth_roles):  # Check for authorized roles in user roles
        return True
    else:
        return False


async def slash_button_ctx(ctx, client):  # Get a Discord context from a SlashContext to send components
    empty = await ctx.send(content="᲼")  # Send an empty message
    # msg= await dc.fetch_component_message(empty)
    ctx = await client.get_context(empty)  # Get the context from it
    await empty.delete()  # Delete the message
    return ctx  # Return the context


# ######################################### EVENTS


# ON GUILD JOIN
@client.event
async def on_guild_join(guild):
    Guild_Manager(guild)


# ON GUILD REMOVE
@client.event
async def on_guild_remove(guild):
    Guild_Manager(guild).del_guild()


# ######################################### COMMANDS


# OPTIONS OF COMMAND BELOW
options = [
    {
        "name": "role",
        "description": "Le role à manager",
        "type": 8,
        "required": True
    },
    {
        "name": "action",
        "description": "Le type d'action que vous voulez effectuer",
        "type": 3,
        "required": True,
        "choices": [
            {
                "name": "Ajouter (PERMETTRE L'ACCES)",
                "value": "add"
            },
            {
                "name": "Supprimer (REFUSER L'ACCES)",
                "value": "del"
            }
        ]
    }
]


# MANAGE AUTHORIZED ROLES
@slash.slash(name="Manage_Authorized_Roles", description="Choisissez les rôles autorisés à utiliser les commandes du bot (Ne s'applique pas a /see_polls)", guild_ids=Guild_Manager.get_all_guilds(), options=options)
async def Manage_Authorized_Roles(sctx, role, action):
    if check_for_auth_roles(sctx.author) or sctx.author.guild_permissions.administrator or sctx.author.top_role.permissions.administrator:
        if action == "add":
            try:
                Guild_Manager(sctx.guild).add_auth_role(role)
                embed = Embed(description=f"{role.mention} ajouté à la liste des rôles autorisés.", color=bot_color)
                await sctx.send(embed=embed, hidden=True)
            except GuildErrors.AuthRoleAlreadyAdded:
                embed = Embed(title="Ce rôle est déjà autorisé", color=bot_color)
                await sctx.send(embed=embed, hidden=True)
        elif action == "del":
            try:
                Guild_Manager(sctx.guild).del_auth_role(role)
                embed = Embed(description=f"{role.mention} supprimé de la liste des rôles autorisés.", color=bot_color)
                await sctx.send(embed=embed, hidden=True)
            except GuildErrors.AuthRoleNotInList:
                embed = Embed(title="Ce rôle n'est déjà pas dans la liste", color=bot_color)
                await sctx.send(embed=embed, hidden=True)
    else:
        embed = Embed(title="Access Denied. Missing permission or role.", color=bot_color)
        await sctx.send(embed=embed, hidden=True)
        return


# POLL
# POLL BAR
def poll_bar(msg_id, guild_id, hidden=False):  # Calculates all lengths of choice bars as well as percentages of votes for each choices returns the description of a poll
    with open("polls.json", "r") as f:  # Openting and getting data from polls.json in read only mode
        polls = json.load(f)
    desc = ""  # Preparing description string
    poll = polls[str(guild_id)][str(msg_id)]  # Getting poll dictionary
    total = poll["total"]  # Total votes

    if hidden:  # Checks if the poll is 'hidden' so it wont show the percentages of votes and the bars will be hidden too if True
        for option in poll["options"].keys():
            desc += f"**{option.capitalize()}**\n\n"  # Add choices to description
        desc += f"Total Votes: {total}"  # Add total number of singular votes to description

    else:  # Else it calculates the percentages of votes for each choices and the bar length of corresponding choice based on the percentage
        for option in poll["options"].keys():
            option_count = poll["options"][option]
            try:  # ########################################### It's a simple percentage calculus with a rounded answer
                option_pct = int((option_count * 100) / total)
                option_bar_count = int(option_pct / 2.5)
                option_bar = "\u258c" * option_bar_count
                desc += f"**{option.capitalize()}**\n{option_bar} **{option_pct}%**\n\n"  # We add the percentage of choice to the description
            except ZeroDivisionError:
                desc += f"**{option.capitalize()}**\n**0%**\n\n"  # If the votes are 0 it simply adds a 0 to the choice
    return desc  # As said above returns the description of poll


# CREATE POLL
options = [
    {"name": "title", "description": "Le titre du vote", "type": 3, "required": True},
    {
        "name": "choices",
        "description": "Les choix (séparez avec '&')",
        "type": 3,
        "required": True,
    },
    {
        "name": "locked",
        "description": "Si Vrai les participants ne peuvent pas modifier leur vote",
        "type": 5,
        "required": False,
    },
    {
        "name": "hidden",
        "description": "Si Vrai les participants ne peuvent pas voir les résultats avant la fin",
        "type": 5,
        "required": False,
    },
]


@slash.slash(
    name="Poll", description="Create Polls", guild_ids=Guild_Manager.get_all_guilds(), options=options
)
async def poll(ctx, title, choices, locked=False, hidden=False):
    sctx = ctx  # Changes name of context object (ctx) to sctx (slash context) for proper separation
    if not check_for_auth_roles(sctx.author):  # Check for staff roles in the command author's role
        em = Embed(title="Vous n'avez pas les permissions d'utiliser cette commande")
        await sctx.send(embed=em, hidden=True)  # If none are found, the embed above is sent to notify them and we return to end the command
        return

    ctx = await slash_button_ctx(sctx, client)  # Else we get the ctx (discord context object) with this command
    opt = []  # Creating an empty list to store the options of poll later
    new_poll = {  # Creating base poll dictionary
        "channel_id": sctx.channel.id,  # <-- The channel ID where the poll was created
        "title": title,  # <-- The title given in parameter
        "options": {},
        "total": 0,
        "users": {},
        "locked": locked,  # <-- Locked parameter
        "hidden": hidden,  # <-- Hidden parameter
    }

    o = 0  # o is for options iteration to keep track of options count
    for option in choices.split("&"):  # We split the choices parameter at every '&' character to get all choices in a list then iterate through it.
        o += 1  # +1 option
        opti = SelectOption(label=option, value=option.lower())  # Create the Select Option object
        new_poll["options"][str(option.lower())] = 0  # Add the option to the dictionary
        opt.append(opti)  # Append the options to the options list

    components = [
        Select(placeholder="Select your choice here", options=opt, max_values=1)  # Creating the Select object in the components list
    ]

    desc = ""  # Creating an empty string for the poll description
    if hidden:  # Check if the hidden parameter is True
        for option in new_poll["options"].keys():  # If so only the choices will be displayed and not the percentages or the visuel bars
            desc += f"**{option.capitalize()}**\n\n"
        desc += "Total Votes: 0"  # At the end we add the total number of singular votes. 0 for now cause we just created it.
    else:  # If hidden is False
        for option in new_poll["options"].keys():  # For each choice no bar will show but only the 0% vote.
            desc += f"**{option.capitalize()}**\n**0%**\n\n"

    em = Embed(title=title, description=desc, color=bot_color)  # We create our embed object with the title given in parameters and the description we just generated.
    if locked:  # Check if the locked parameter is True
        em.set_footer(text="Une fois que vous avez fait votre choix vous ne pourrez plus le modifier. Réfléchissez !")  # If so adds a footer to warn voters
    try:  # Try to send the message to the context
        msg = await ctx.send(embed=em, components=components)  # In the message are the embed and the Select onject in components list
    except discord.errors.HTTPException:  # If there is an HTTPException it means there is 2 or more choices that are exactly the same
        em = Embed(title="You can't put the same choice twice.", color=bot_color)
        await sctx.send(embed=em, hidden=True)  # So we send a message to notify the usera about it and return to end the command
        return

    with open("polls.json", "r") as f:  # Here we open the polls.json file in read mode
        polls = json.load(f)  # We load the file content in a python readable json object
    polls[str(sctx.guild.id)][str(msg.id)] = new_poll  # We add the poll to the file by having the poll message ID as the key and the dictionary as the value
    with open("polls.json", "w") as f:  # Then we open the polls.json file in write mode
        json.dump(polls, f, indent=4)  # And dump (write) the data into the file

    get_poll.restart()  # We then restart the get_poll function to update the file for the task


# STOP POLL
async def fetch_poll_options(guild_id):  # Fetches all currently stored polls to display their name
    with open("polls.json", "r") as f:  # Open polls.json file in read mode
        polls = json.load(f)  # Load the json file into a python readable json object

    options = []  # Create an empty list to store all the options (options will be the polls that can be ended)
    for key in polls[str(guild_id)].keys():  # For each key in the poll's json object
        msg_id = key  # We get the message ID which is the key
        poll = polls[key]  # We get the poll dictionary
        title = poll["title"]  # And the title of the poll
        options.append(SelectOption(label=title, value=msg_id))  # We then create and append a SelectOption that contains the title of the poll

    return options  # Once the parsing is over we return the results in the form of a list which is the options list


@slash.slash(name="End_Poll", description="Stop a poll", guild_ids=Guild_Manager.get_all_guilds())
async def end_poll(ctx):  # Command that lets you end polls that are stored in the data file and currently running
    sctx = ctx  # We rename the ctx (discord context) to sctx (SlashContext) for better readability
    if not check_for_auth_roles(sctx.author):  # Checking for staff roles in the command author's roles
        em = Embed(title="Vous n'avez pas les permissions d'utiliser cette commande")
        await sctx.send(embed=em, hidden=True)  # If there isn't a message is sent to the user to notify them and we return to end the command
        return

    ctx = await slash_button_ctx(ctx, client)  # Getting the ctx (discord context) from the sctx
    with open("polls.json", "r") as f:  # Opening the polls.json file in read mode
        polls = json.load(f)  # Loading the file data into a python json readable object

    if polls == {}:  # Checking if the file is empty (If there is no running polls)
        em = Embed(title="There is no polls to end", color=bot_color)
        await sctx.send(embed=em, hidden=True)  # If so a message is sent to the user to notify them and we return to end the command
        return

    em = Embed(title="Chose a poll to end", color=bot_color)  # In the next two lines we create an embed and fetch all the polls that can be ended
    options = await fetch_poll_options(sctx.author.guild.id)
    components = [Select(placeholder="Select a poll to end", options=options)]  # Then we create our components list containing a Select object with the polls as options

    msg = await ctx.send(embed=em, components=components)  # We send the message containing the Select and store it into a variable
    res = await client.wait_for("select_option", check=lambda i: i.author == sctx.author and i.channel == sctx.channel)  # We wait for the author of the commands to pick an option
    await msg.delete()  # Then we delete the message send previously

    key = res.values[0]  # The key to get the poll that was stored in the SelectOption the user picked. The SelectOptions were generated by await fetch_poll_options()
    poll = polls[key]  # We get the poll dictionary
    message_id = key  # We restore the key into a new variable for readability
    channel = client.get_channel(poll["channel_id"])  # We get the channel object of the poll's channel
    desc = poll_bar(key, sctx.guild.id)  # We call poll_bar to generate the bar for the final results

    p_msg = await channel.fetch_message(message_id)  # We get the poll message as p_msg
    await p_msg.delete()  # We delete the poll message

    em = Embed(title=f"Result For Poll | {poll['title']}", description=desc, color=bot_color, timestamp=datetime.datetime.utcnow())  # Create a new embed to send the results of the poll
    em.add_field(name="Total Sigular Answers", value=poll["total"])  # Add the number of total singular answers as a field

    del polls[key]  # We then delete the disctionary of the poll from the file

    with open("polls.json", "w") as f:  # We open the polls.json file in write mode
        json.dump(polls, f, indent=4)  # Then we dump (write) the new data inside of it

    await channel.send(embed=em)  # We send the result embed to the poll channel
    await sctx.send(f"'{poll['title']}' Poll ended", hidden=True)  # And we send a confirmation message that is visible by the command author only
    get_poll.restart()  # And we restart the get_poll() task to update its variable of the polls.json file


# SEE POLLS
async def fetch_polls(guild_id):  # Fetch the polls to display their title total number of choices and total votes, the title is a hyperlink to the poll
    with open("polls.json", "r") as f:  # Open the polls.json file
        polls = json.load(f)  # Load the file data into a python readable json object

    polls_list = ""  # Create and empty string to store the list of polls later

    for key in polls[str(guild_id)].keys():  # iterate through reach poll key
        poll = polls[key]  # Get the poll dictionary
        title = poll["title"]  # Get the poll title
        msg_id = key  # Store the key into msg_id for readability
        channel = client.get_channel(poll["channel_id"])  # Get the poll's channel object
        msg = await channel.fetch_message(msg_id)  # Get the poll's message object
        url = str(msg.jump_url)  # Get the jump url to the poll message
        total = poll["total"]  # Get the total number of votes
        choices = len(poll["options"])  # Get the total number of options
        polls_list += f"[**{title}**]({url} 'See The Poll') | Total Choices: `{choices}` | Total Votes: `{total}`\n"  # Append the string of the poll to the polls list

    if polls_list == "":  # Check if polls list is empty
        polls_list = None  # If so it will be equal to None

    return polls_list  # Return the polls list


@slash.slash(name="See_Polls", description="See all active polls", guild_ids=Guild_Manager.get_all_guilds())
async def see_polls(ctx):  # Commands that lets you see all the running polls
    polls_list = await fetch_polls(ctx.guild.id)  # Get polls list

    if polls_list is None:  # Check if polls list is None (Empty)
        em = Embed(title="There is no polls", color=bot_color)
        await ctx.send(embed=em, hidden=True)  # If so a message is sent to notify the user and we return to end the command
        return

    em = Embed(title="Polls", description=polls_list, color=bot_color)  # Creating embed with polls list as description
    await ctx.send(embed=em, hidden=True)  # Send the embed as a hidden message for privacy and to not flood the chat


# GET POLL
@tasks.loop(minutes=60)  # This task is called every hour
async def get_poll():  # Gets all polls interactions
    while True:  # Infinite loop to get all interactions all the time
        with open("polls.json", "r") as f:  # Open polls.json file
            polls = json.load(f)  # Load file data into a python readable json object

        res = await client.wait_for("select_option", check=lambda i: any(str(i.message.id) == key for key in polls[str(i.author.guild.id)].keys()))  # Wait for an interaction and check if interaction
        values = res.values  # Get selected option                                                                           # message's ID is in polls.json
        print(res.author.guild.id)

        if str(res.message.id) in polls[str(res.author.guild.id)].keys():  # If the message ID is in the keys of polls.json
            poll = polls[str(res.message.id)]  # Get the poll
            users = polls[str(res.message.id)]["users"]  # Get all the users that voted
            locked = polls[str(res.message.id)]["locked"]  # Get if the poll is locked or not
            hidden = polls[str(res.message.id)]["hidden"]  # Get id the poll is hidden or not

            if str(res.author.id) in users.keys():  # Check if user has already voted
                if locked:  # If so check if poll is locked
                    await res.send(content="You can't change your vote. Sorry !")  # If it is we send a message to notify the user he can't change his vote and
                    continue                                                       # continue the loop to wait for the next interaction

                await res.send(content=f"You selected '**{res.values[0].capitalize()}**'")  # Send the user a confirmation message of their choice that only them can see
                user_choice = users[str(res.author.id)]  # Get the user's previous choice
                poll["options"][user_choice] -= 1  # Substract one to the count of previous choice
                poll["options"][values[0]] += 1  # Add one to the count of new choice
                users[str(res.author.id)] = values[0]  # Change user's choice name to new choice
            else:  # I user hasn't voted yet
                await res.send(content=f"You selected '**{res.values[0].capitalize()}**'")  # Send the user a confirmation message of their choice that only them can see
                poll["users"][str(res.author.id)] = values[0]  # Set user's choice name to selected option
                poll["options"][values[0]] += 1  # Add one to selected option count
                poll["total"] += 1  # Add one to total singular votes

            with open("polls.json", "w") as f:  # Open polls.json in write mode
                json.dump(polls, f, indent=4)  # Dump (write) new data (changes) into polls.json

            if not hidden:  # Check if poll has the hidden option to False
                desc = poll_bar(str(res.message.id), res.author.guild.id)  # If so we call the normal poll_bar() function
            else:
                desc = poll_bar(str(res.message.id), res.author.guild.id, hidden=True)  # If not we call it with the hidden parameter to True
            em = Embed(title=poll["title"], description=desc, color=bot_color)  # We add the descrtiption to the poll embed

            if locked:  # Check if the locked parameter is True
                em.set_footer(text="Une fois que vous avez fait votre choix vous ne pourrez plus le modifier. Réfléchissez !")  # If so we add a message to notify user
            await res.message.edit(embed=em)  # Then we sen the updated poll embed


@slash.slash(name="Doc", description="Code Source, Manuel et Invitations", guild_ids=Guild_Manager.get_all_guilds())
async def Doc(sctx):
    embed = Embed(title="Bot Documentation", description="[**GitHub Repository du Source Code**](https://github.com/Shaqalito/DirtyVotes)\n[**Mon Profil**](https://github.com/Shaqalito)\n[**Manuel du Bot**](https://docs.google.com/document/d/1G5D5VPSxPdHqOK-KZx06OZN1cOMldHzQKkxx-2iMC48/edit?usp=sharing)\n[**Inviter le Bot**](https://discord.com/api/oauth2/authorize?client_id=909477659136909333&permissions=8&scope=bot%20applications.commands)", color=bot_color)
    await sctx.send(embed=embed, hidden=True)

keep_alive()
client.run(os.getenv("TOKEN"))
