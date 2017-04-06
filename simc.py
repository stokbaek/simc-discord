import os
import sys
import subprocess
import discord
import aiohttp
import asyncio
import time
import json
from urllib.parse import quote

os.chdir(os.path.dirname(os.path.abspath(__file__)))
with open('user_data.json') as data_file:
    user_opt = json.load(data_file)

bot = discord.Client()
simc_opts = user_opt['simcraft_opt'][0]
server_opts = user_opt['server_opt'][0]
threads = os.cpu_count()
if 'threads' in simc_opts:
    threads = simc_opts['threads']
process_priority = 'below_normal'
if 'process_priority' in simc_opts:
    process_priority = simc_opts['process_priority']
htmldir = simc_opts['htmldir']
website = simc_opts['website']
os.makedirs(os.path.dirname(os.path.join(htmldir + 'debug', 'test.file')), exist_ok=True)
waiting = False
busy = False
busytime = 0
user = ''
api_key = simc_opts['api_key']
sims = {}


def check_version():
    git = subprocess.check_output(['git', 'rev-parse', '--is-inside-work-tree']).decode(sys.stdout.encoding)
    if git:
        for line in subprocess.check_output(['git', 'remote', '-v']).decode(sys.stdout.encoding).split('\n'):
            if 'https' in line and '(fetch)' in line:
                subprocess.Popen(['git', 'fetch'], universal_newlines=True, stderr=None, stdout=None)
                for output in subprocess.check_output(['git', 'status']).decode(sys.stdout.encoding).split('\n'):
                    if 'Your branch is' in output:
                        if 'up-to-date' in output:
                            return 'Bot is up to date'
                        elif 'behind' in output:
                            return 'Update available for bot'
                        else:
                            return 'Bot version unknown'
            elif 'git@github.com' in git and '(fetch)' in git:
                return 'Bot version unknown'
    else:
        return 'Bot version unknown'


def check_simc():
    null = open(os.devnull, 'w')
    stdout = open(os.path.join(htmldir, 'debug', 'simc.ver'), "w")
    subprocess.Popen(simc_opts['executable'], universal_newlines=True, stderr=null, stdout=stdout)
    time.sleep(1)
    with open(os.path.join(htmldir, 'debug', 'simc.stout'), errors='replace') as v:
        version = v.readline().rstrip('\n')
    return version


async def check_spec(region, realm, char, api_key):
    url = "https://%s.api.battle.net/wow/character/%s/%s?fields=talents&locale=en_GB&apikey=%s" % (region, realm,
                                                                                                   quote(char), api_key)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if 'reason' in data:
                return data['reason']
            else:
                spec = 0
                for i in range(len(data['talents'])):
                    for line in data['talents']:
                        if 'selected' in line:
                            role = data['talents'][spec]['spec']['role']
                            return role
                        else:
                            spec += +1


async def sim():
    global sims
    global busy
    while not busy:
        busy = True
        sim_user = list(sorted(sims))[0]
        filename = '%s-%s' % (sims[sim_user]['char'], sims[sim_user]['timestr'])
        link = 'Simulation: %ssims/%s/%s.html' % (website, sims[sim_user]['char'], filename)
        message = sims[sim_user]['message']
        loop = True
        scale_stats = 'agility,strength,intellect,crit_rating,haste_rating,mastery_rating,versatility_rating'
        options = 'calculate_scale_factors=%s scale_only=%s html=%ssims/%s/%s.html threads=%s iterations=%s ' \
                  'fight_style=%s enemy=%s apikey=%s process_priority=%s max_time=%s' % (sims[sim_user]['scale'],
                                                                                         scale_stats, htmldir,
                                                                                         sims[sim_user]['char'],
                                                                                         filename,
                                                                                         threads, sims[sim_user][
                                                                                             'iterations'],
                                                                                         sims[sim_user]['fightstyle'],
                                                                                         sims[sim_user]['enemy'],
                                                                                         api_key,
                                                                                         process_priority,
                                                                                         sims[sim_user][
                                                                                             'length'])
        if sims[sim_user]['data'] == 'addon':
            options += ' input=%s' % sims[sim_user]['d_addon']
        else:
            options += ' armory=%s,%s,%s' % (sims[sim_user]['region'], sims[sim_user]['realm'], sims[sim_user]['char'])

        if sims[sim_user]['l_fixed'] == 1:
            options += ' vary_combat_length=0.0 fixed_time=1'

        await bot.change_presence(status=discord.Status.dnd, game=discord.Game(name='Sim: In Progress'))
        msg = '\nSimulationCraft:\nRealm: %s\nCharacter: %s\nFightstyle: %s\nFight Length: %s\nAoE: %s\n' \
              'Iterations: %s\nScaling: %s\nData: %s' % (
                  sims[sim_user]['realm'].capitalize(), sims[sim_user]['char'].capitalize(),
                  sims[sim_user]['movements'],
                  sims[sim_user]['length'], sims[sim_user]['aoe'].capitalize(), sims[sim_user]['iterations'],
                  sims[sim_user]['scaling'].capitalize(), sims[sim_user]['data'].capitalize())
        await bot.send_message(sims[sim_user]['message'].channel, msg)
        load = await bot.send_message(sims[sim_user]['message'].channel, 'Simulating: Starting...')
        command = "%s %s" % (simc_opts['executable'], options)
        stout = open(os.path.join(htmldir, 'debug', 'simc.stout'), "w")
        sterr = open(os.path.join(htmldir, 'debug', 'simc.sterr'), "w")
        process = subprocess.Popen(command.split(" "), universal_newlines=True, stdout=stout, stderr=sterr)
        await asyncio.sleep(1)
        while loop:
            await asyncio.sleep(1)
            with open(os.path.join(htmldir, 'debug', 'simc.stout'), errors='replace') as p:
                process_check = p.readlines()
            with open(os.path.join(htmldir, 'debug', 'simc.sterr'), errors='replace') as e:
                err_check = e.readlines()
            if len(err_check) > 0:
                if 'ERROR' in err_check[-1]:
                    await bot.change_presence(status=discord.Status.online, game=discord.Game(name='Sim: Ready'))
                    await bot.edit_message(load, 'Error, something went wrong: ' + website + 'debug/simc.sterr')
                    process.terminate()
                    del sims[sim_user]
                    return
            if len(process_check) > 1:
                if 'report took' in process_check[-2]:
                    loop = False
                    await bot.change_presence(status=discord.Status.online, game=discord.Game(name='Sim: Ready'))
                    await bot.edit_message(load, link + ' {0.author.mention}'.format(message))
                    process.terminate()
                    busy = False
                    del sims[sim_user]
                    if len(sims) != 0:
                        bot.loop.create_task(sim())
                    else:
                        return
                else:
                    if 'Generating' in process_check[-1]:
                        done = '█' * (20 - process_check[-1].count('.'))
                        missing = '░' * (process_check[-1].count('.'))
                        progressbar = done + missing
                        percentage = 100 - process_check[-1].count('.') * 5
                        load = await bot.edit_message(load, process_check[-1].split()[1] + ' ' + progressbar + ' ' +
                                                      str(percentage) + '%')


def check(addon_data):
    return addon_data.content.endswith('DONE')


@bot.event
async def on_message(message):
    global busy
    global user
    global sims
    global api_key
    global waiting
    m_temp = ''
    a_temp = ''
    server = bot.get_server(server_opts['serverid'])
    channel = bot.get_channel(server_opts['channelid'])

    timestr = time.strftime("%Y%m%d-%H%M%S")
    args = message.content.lower()
    if message.author == bot.user:
        return
    elif args.startswith('!simc'):
        user = timestr + '-' + str(message.author)
        user_sim = {user: {'realm': simc_opts['default_realm'],
                           'region': simc_opts['region'],
                           'iterations': simc_opts['default_iterations'],
                           'scale': 0,
                           'scaling': 'no',
                           'data': 'armory',
                           'char': '',
                           'aoe': 'no',
                           'enemy': '',
                           'd_addon': '',
                           'fightstyle': simc_opts['fightstyles'][0],
                           'movements': '',
                           'length': simc_opts['length'],
                           'l_fixed': 0,
                           'timestr': time.strftime("%Y%m%d-%H%M%S"),
                           'message': '',
                           'run': False
                           }
                    }
        sims.update(user_sim)
        for key in sims[user]:
            if key == 'message':
                sims[user]['message'] = message
        args = args.split('-')
        if args:
            if args[1].startswith(('h', 'help')):
                with open('help.file', errors='replace') as h:
                    msg = h.read()
                await bot.send_message(message.author, msg)
            elif args[1].startswith(('v', 'version')):
                await bot.send_message(message.channel, check_version())
                await bot.send_message(message.channel, check_simc())
            else:
                if message.channel != channel:
                    await bot.send_message(message.channel, 'Please use the correct channel.')
                    return
                if args[1].startswith(('q', 'queue')):
                    if busy:
                        await bot.send_message(message.channel,
                                               'Queue: %s/%s' % (len(sims), server_opts['queue_limit']))
                    else:
                        await bot.send_message(message.channel, 'Queue is empty')
                    return
                if busy:
                    if len(sims) > server_opts['queue_limit'] - 1:
                        await bot.send_message(sims[user]['message'].channel,
                                               '**Queue is full, please try again later.**')
                        return
                    if waiting:
                        await bot.send_message(sims[user]['message'].channel,
                                               '**Waiting for simc addon data from %s.**' %
                                               sims[user]['message'].author.display_name)
                        return
                for i in range(len(args)):
                    if args[i] != '!simc ':
                        if args[i].startswith(('r ', 'realm ')):
                            temp = args[i].split()
                            for key in sims[user]:
                                if key == 'realm':
                                    sims[user]['realm'] = temp[1]
                        elif args[i].startswith(('c ', 'char ', 'character ')):
                            temp = args[i].split()
                            for key in sims[user]:
                                if key == 'char':
                                    sims[user]['char'] = temp[1]
                        elif args[i].startswith(('s ', 'scaling ')):
                            temp = args[i].split()
                            for key in sims[user]:
                                if key == 'scaling':
                                    sims[user]['scaling'] = temp[1]
                        elif args[i].startswith(('d ', 'data ')):
                            temp = args[i].split()
                            for key in sims[user]:
                                if key == 'data':
                                    sims[user]['data'] = temp[1]
                        elif args[i].startswith(('i ', 'iterations ')):
                            if simc_opts['allow_iteration_parameter']:
                                temp = args[i].split()
                                for key in sims[user]:
                                    if key == 'iterations':
                                        sims[user]['iterations'] = temp[1]
                            else:
                                await bot.send_message(message.channel, 'Custom iterations is disabled')
                                return
                        elif args[i].startswith(('f ', 'fight ', 'fightstyle ')):
                            fstyle = False
                            temp = args[i].split()
                            for opt in range(len(simc_opts['fightstyles'])):
                                if temp[1] == simc_opts['fightstyles'][opt].lower():
                                    for key in sims[user]:
                                        if key == 'fightstyle':
                                            sims[user]['fightstyle'] = temp[1]
                                    fstyle = True
                            if fstyle is not True:
                                await bot.send_message(message.channel, 'Unknown fightstyle.\nSupported Styles: ' +
                                                       ', '.join(simc_opts['fightstyles']))
                                return
                        elif args[i].startswith(('a ', 'aoe ')):
                            temp = args[i].split()
                            for key in sims[user]:
                                if key == 'aoe':
                                    sims[user]['aoe'] = temp[1]
                        elif args[i].startswith(('l ', 'length ')):
                            temp = args[i].split()
                            for key in sims[user]:
                                if key == 'length':
                                    sims[user]['length'] = temp[1]
                            if len(temp) > 2:
                                if temp[2] == 'fixed':
                                    for key in sims[user]:
                                        if key == 'l_fixed':
                                            sims[user]['l_fixed'] = 1
                        else:
                            await bot.send_message(message.channel, 'Unknown command. Use !simc -h/help for commands')
                            return
                if sims[user]['char'] == '':
                    await bot.send_message(message.channel, 'Character name is needed')
                    return
                if sims[user]['scaling'] == 'yes':
                    for key in sims[user]:
                        if key == 'scale':
                            sims[user]['scale'] = 1
                if sims[user]['aoe'] == 'yes':
                    for targets in range(0, simc_opts['aoe_targets']):
                        targets += + 1
                        a_temp += 'enemy=target%s ' % targets
                    for key in sims[user]:
                        if key == 'enemy':
                            sims[user]['enemy'] = a_temp

                os.makedirs(os.path.dirname(os.path.join(htmldir + 'sims', sims[user]['char'], 'test.file')),
                            exist_ok=True)

                if sims[user]['data'] == 'addon':
                    waiting = True
                    while waiting:
                        await bot.change_presence(status=discord.Status.idle, game=discord.Game(name='Sim: Waiting...'))
                        msg = 'Please paste the output of your simulationcraft addon here and finish with DONE'
                        await bot.send_message(message.author, msg)
                        addon_data = await bot.wait_for_message(author=message.author, check=check, timeout=60)
                        if addon_data is None:
                            await bot.send_message(message.author, 'No data given. Resetting session.')
                            await bot.change_presence(status=discord.Status.online,
                                                      game=discord.Game(name='Sim: Ready'))
                            waiting = False
                            return
                        else:
                            healing_roles = ['restoration', 'holy', 'discipline', 'mistweaver']
                            sims[user]['addon'] = '%ssims/%s/%s-%s.simc' % (
                            htmldir, sims[user]['char'], sims[user]['char'], timestr)
                            f = open(sims[user]['addon'], 'w')
                            f.write(addon_data.content[:-4])
                            f.close()
                            for crole in healing_roles:
                                crole = 'spec=' + crole
                                if crole in addon_data.content:
                                    await bot.send_message(message.channel,
                                                           'SimulationCraft does not support healing.')
                                    await bot.change_presence(status=discord.Status.online,
                                                              game=discord.Game(name='Sim: Ready'))
                                    waiting = False
                                    return
                            waiting = False

                if sims[user]['data'] != 'addon':
                    api = await check_spec(sims[user]['region'], sims[user]['realm'], sims[user]['char'], api_key)
                    if api == 'HEALING':
                        await bot.send_message(message.channel, 'SimulationCraft does not support healing.')
                        return
                    elif not api == 'DPS' and not api == 'TANK':
                        msg = 'Something went wrong: %s' % api
                        await bot.send_message(message.channel, msg)
                        return
                for item in simc_opts['fightstyles']:
                    if item.lower() == sims[user]['fightstyle'].lower():
                        m_temp = m_temp + '**__' + item + '__**, '
                    else:
                        m_temp = m_temp + item + ', '
                for key in sims[user]:
                    if key == 'movements':
                        sims[user]['movements'] = m_temp
                for key in sims[user]:
                    if key == 'run':
                        sims[user]['run'] = True
                if sims[user]['run']:
                    bot.loop.create_task(sim())
                else:
                    del sims[user]


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print(check_version())
    print(check_simc())
    print('--------------')
    await bot.change_presence(game=discord.Game(name='Simulation: Ready'))


bot.run(server_opts['token'])
