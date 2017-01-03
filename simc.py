import os
import discord
import asyncio
import time
import user_data

client = discord.Client()


async def sim(realm, char, scale, htmladdr, data, addon, loop, message):
    icon_num = 0
    load_icon = ['◐', '◓', '◑', '◒']
    if data == 'addon':
        options = 'calculate_scale_factors=%s html=/var/www/html/simc/%s threads=8 iterations=24999 input=%s' % (
            scale, htmladdr, addon)
    else:
        options = 'armory=eu,%s,%s calculate_scale_factors=%s html=/var/www/html/simc/%s threads=8 iterations=24999' % (
            realm, char, scale, htmladdr)

    load = await client.send_message(message.channel, 'Simulating: '+load_icon[icon_num])
    os.system('/usr/local/sbin/simc %s &' % options)
    while loop:
        if os.path.exists('/var/www/html/simc/%s' % htmladdr):
            loop = False
            link = 'Simulation: https://stokbaek.org/simc/%s' % htmladdr
            await client.change_presence(status=discord.Status.online, game=discord.Game(name='Sim: Ready'))
            await client.edit_message(load, link)
        else:
            load = await client.edit_message(load, 'Simulating: '+load_icon[icon_num])
            await asyncio.sleep(1)
            icon_num += 1
            if icon_num == 4:
                icon_num = 0


@client.event
async def on_message(message):
    server = client.get_server(user_data.serverid)
    loop = True
    timestr = time.strftime("%Y%m%d-%H%M%S")
    realm = 'magtheridon'
    scale = 0
    scaling = 'No'
    data = 'armory'
    char = 'Dummy'
    addon = 'Dummy'

    def check(addon_data):
        return addon_data.content.endswith('DONE')
    if message.author == client.user:
        return
    if message.content.startswith('!simc'):
        args = message.content.split('-')
        if args:
            if args[1].startswith(('h', 'help')):
                msg = open('help.file', 'r').read()
                await client.send_message(message.author, msg)
            else:
                for i in range(len(args)):
                    if args[i].startswith(('r ', 'realm ')):
                        temp = args[i].split()
                        realm = temp[1]
                    elif args[i].startswith(('c ', 'char ', 'character ')):
                        temp = args[i].split()
                        char = temp[1]
                    elif args[i].startswith(('s ', 'scaling ')):
                        temp = args[i].split()
                        scaling = temp[1]
                    elif args[i].startswith(('d ', 'data ')):
                        temp = args[i].split()
                        data = temp[1]
                if server.me.status != discord.Status.online:
                    err_msg = 'Only one simulation can run at the same time.'
                    await client.send_message(message.channel, err_msg)
                    return
                else:
                    if char != 'Dummy':
                        if scaling == 'yes':
                            scale = 1
                        user = message.author
                        if data == 'addon':
                            await client.change_presence(status=discord.Status.idle,
                                                         game=discord.Game(name='Sim: Waiting...'))
                            msg = 'Please paste the output of your simulationcraft addon here and finish with DONE'
                            await client.send_message(user, msg)
                            addon_data = await client.wait_for_message(author=message.author, check=check, timeout=60)
                            if addon_data is None:
                                await client.send_message(message.channel, 'No data given. Resetting session.')
                                await client.change_presence(status=discord.Status.online,
                                                             game=discord.Game(name='Sim: Ready'))
                                return
                            else:
                                addon = '/var/www/html/simc/%s.simc' % char
                                f = open(addon, 'w')
                                f.write(addon_data.content[:-4])
                                f.close()
                        await client.change_presence(status=discord.Status.dnd,
                                                     game=discord.Game(name='Sim: In Progress'))
                        msg = '\nSimulationCraft:\nRealm: %s\nCharacter: %s\nScaling: %s\nData: %s' % (
                            realm.capitalize(), char.capitalize(), scaling.capitalize(), data.capitalize())
                        htmladdr = '%s-%s.html' % (char, timestr)
                        await client.send_message(message.channel, msg)
                        client.loop.create_task(sim(realm, char, scale, htmladdr, data, addon, loop, message))


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    await client.change_presence(game=discord.Game(name='Simulation: Ready'))

client.run(user_data.TOKEN)
