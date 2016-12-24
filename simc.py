import os
import argparse
import discord
import asyncio
import time
import sys
import user_data
from subprocess import PIPE, run

client = discord.Client()

async def sim(REALM, CHAR, SCALE, HTMLADDR, DATA, ADDON, LOOP, message):
    icon_num = 0
    load_icon = ['◐', '◓', '◑', '◒']
    if DATA == 'addon':
        OPTIONS = 'calculate_scale_factors=%s html=/var/www/html/simc/%s threads=8 iterations=24999 input=%s' % (SCALE, HTMLADDR, ADDON)
    else:
        OPTIONS = 'armory=eu,%s,%s calculate_scale_factors=%s html=/var/www/html/simc/%s threads=8 iterations=24999' % (REALM, CHAR, SCALE, HTMLADDR)

    load = await client.send_message(message.channel, 'Simulating: '+load_icon[icon_num])
    os.system('/usr/local/sbin/simc %s &' % (OPTIONS))
    while LOOP:
        if os.path.exists('/var/www/html/simc/%s' % HTMLADDR):
            LOOP = False
            link = 'Simulation: https://stokbaek.org/simc/%s' % (HTMLADDR)
            await client.change_presence(status=discord.Status.online, game=discord.Game(name='Sim: Ready'))
            await client.edit_message(load, link)
        else:
            load = await client.edit_message(load, 'Simulating: '+load_icon[icon_num])
            await asyncio.sleep(1)
            icon_num = icon_num + 1
            if icon_num == 4:
                icon_num = 0


@client.event
async def on_message(message):
    server = client.get_server(user_data.serverid)
    LOOP = True
    USER = 'Dummy'
    TIMESTR = time.strftime("%Y%m%d-%H%M%S")
    REALM = 'magtheridon'
    SCALE = 0
    SCALING = 'No'
    DATA = 'armory'
    CHAR = 'Dummy'
    HTMLADDR = 'Dummy'
    ADDON = 'Dummy'

    def check(addon_data):
        return addon_data.content.endswith('DONE')
    if message.author == client.user:
        return
    if message.content.startswith('!simc'):
        args = message.content.split('-')
        if args:
            if args[1].startswith(('h', 'help')):
                msg = ('***Help for simulation through Discord:***\n'
                       ' ***Options:***\n'
                       '-c	-character 	**InGame name**\n'
                       '-r	-realm		**Realm** *(Default is Magtheridon)*\n'
                       '-s	-scale		**yes/no** *(Default is no)*\n'
                       '-d	-data		**armory/addon** *(Default is armory)*\n\n'
                       ' ● Simulate using armory with stat scaling:\n\n'
                       '`!simc -character NAME -scale yes`\n\n'
                       ' ● Simulate using addon without stat scaling:\n\n'
                       '`!simc -character NAME -d addon`\n\n'
                       '*The bot will whisper asking for a paste of data string from the addon ingame. The last line should contain DONE.*\n'
                       '__example__\n'
                       '```warlock="Stokbaek"\n'
                       'level=110\n'
                       'race=goblin\n'
                       'region=eu\n'
                       'server=magtheridon\n'
                       'role=attack\n'
                       'professions=alchemy=784/herbalism=800\n'
                       'talents=1131323\n'
                       'spec=destruction\n'
                       'artifact=38:0:0:0:0:803:1:807:3:808:2:809:3:810:3:811:3'
                       ':812:3:814:1:815:1:817:1:818:1:1355:1\n\n'
                       'head=,id=139909,bonus_id=665\n'
                       'neck=,id=139332,enchant_id=5439,bonus_id=1807/1808/1472\n'
                       'shoulder=,id=134221,bonus_id=3416/1532/3336\n'
                       'back=,id=139248,bonus_id=1805/1808/1492/3336\n'
                       'chest=,id=142410,bonus_id=3468/1808/1492\n'
                       'wrist=,id=142415,bonus_id=3467/1497/3337\n'
                       'hands=,id=140993,bonus_id=1805/1487\n'
                       'waist=,id=142153,bonus_id=3452/1487/3337\n'
                       'legs=,id=139190,bonus_id=1805/1487\n'
                       'feet=,id=134308,bonus_id=3415/1522/3336\n'
                       'finger1=,id=132452,enchant_id=5428,bonus_id=3459/3458\n'
                       'finger2=,id=142520,enchant_id=5428,bonus_id=3467/1492/3337\n'
                       'trinket1=,id=137301,bonus_id=3509/1532/3336\n'
                       'trinket2=,id=142157,bonus_id=41/3453/1472\n'
                       'main_hand=,id=128941,bonus_id=749,relic_id=3506:1482/3467:1477/3453:1472,gem_id=0/0/0/0\n'
                       'DONE```')
                await client.send_message(message.author, msg)
            else:
                for i in range(len(args)):
                    if args[i].startswith(('r ', 'realm ')):
                        TEMP = args[i].split()
                        REALM = TEMP[1]
                    elif args[i].startswith(('c ', 'char ', 'character ')):
                        TEMP = args[i].split()
                        CHAR = TEMP[1]
                    elif args[i].startswith(('s ', 'scaling ')):
                        TEMP = args[i].split()
                        SCALING = TEMP[1]
                    elif args[i].startswith(('d ', 'data ')):
                        TEMP = args[i].split()
                        DATA = TEMP[1]
                if server.me.status != discord.Status.online:
                    err_msg = 'Only one simulation can run at the same time.'
                    await client.send_message(message.channel, err_msg)
                    return
                else:
                    if CHAR != 'Dummy':
                        if SCALING == 'yes':
                            SCALE = 1
                        USER = message.author
                        if DATA == 'addon':
                            await client.change_presence(status=discord.Status.idle, game=discord.Game(name='Sim: Waiting...'))
                            msg = 'Please paste the output of your simulationcraft addon here and finish with DONE'
                            await client.send_message(USER, msg)
                            ADDON_DATA = await client.wait_for_message(author=message.author, check=check, timeout=60)
                            if ADDON_DATA is None:
                                await client.send_message(message.channel, 'No data given. Resetting sesion.')
                                await client.change_presence(status=discord.Status.online, game=discord.Game(name='Sim: Ready'))
                                return
                            else:
                                ADDON = '/var/www/html/simc/%s.simc' % CHAR
                                f = open(ADDON, 'w')
                                f.write(ADDON_DATA.content[:-4])
                                f.close()
                        await client.change_presence(status=discord.Status.dnd, game=discord.Game(name='Sim: In Progress'))
                        msg = '\nSimulationCraft:\nRealm: %s\nCharacter: %s\nScaling: %s\nData: %s' % (REALM.capitalize(), CHAR.capitalize(), SCALING.capitalize(), DATA.capitalize())
                        HTMLADDR = '%s-%s.html' % (CHAR, TIMESTR)
                        await client.send_message(message.channel, msg)
                        client.loop.create_task(sim(REALM, CHAR, SCALE, HTMLADDR, DATA, ADDON, LOOP, message))


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await client.change_presence(game=discord.Game(name='Simulation: Ready'))

client.run(user_data.TOKEN)
