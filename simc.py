import os
import sys
import subprocess
import discord
import aiohttp
import asyncio
import json
import logging
import time
from datetime import datetime
from urllib.parse import quote

os.chdir(os.path.dirname(os.path.abspath(__file__)))
with open('user_data.json') as data_file:
    user_opt = json.load(data_file)

simc_opts = user_opt['simcraft_opt'][0]
server_opts = user_opt['server_opt'][0]

logger = logging.getLogger('discord')
level = logging.getLevelName(server_opts['loglevel'])
logger.setLevel(level)
handler = logging.FileHandler(filename=server_opts['logfile'], encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

bot = discord.Client()
server = bot.get_server(server_opts['serverid'])
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
    try:
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
                                logger.info('Update available for bot.')
                                return 'Update available for bot'
                            else:
                                logger.warning('Bot cant check version:  Local changes made?')
                                return 'Bot version unknown'
                        elif 'On branch' in output:
                            logger.warning('Bot cant check version: Is it on a branch?')
                            return 'Bot version unknown'

                elif 'git@github.com' in git and '(fetch)' in git:
                    logger.warning(
                        'Bot cant check version: Git is not set up correcly for bot to be able to check its version.')
                    return 'Bot version unknown'
        else:
            logger.warning('Bot cant check version: Unknown git error.')
            return 'Bot version unknown'
    except:
        logger.warning('Cannot connect to github.')
        pass


def check_simc():
    null = open(os.devnull, 'w')
    stdout = open(os.path.join(htmldir, 'debug', 'simc.ver'), "w")
    try:
        subprocess.Popen(simc_opts['executable'], universal_newlines=True, stderr=null, stdout=stdout)
    except FileNotFoundError as e:
        logger.critical('Simulationcraft program could not be run. (ERR: %s)' %e)
        time.sleep(1)
    with open(os.path.join(htmldir, 'debug', 'simc.stout'), errors='replace') as v:
        version = v.readline().rstrip('\n')
    return version

async def set_status():
    if waiting:
        try:
            await bot.change_presence(status=discord.Status.idle, game=discord.Game(name='Sim: Waiting...'))
        except:
            logger.warning('Failed to set presence for addon data input.')
            pass
    if len(sims) == server_opts['queue_limit']:
        try:
            await bot.change_presence(status=discord.Status.dnd,
                                      game=discord.Game(name='Sim: %s/%s' % (len(sims), server_opts['queue_limit'])))
        except:
            logger.warning('Failed to set presence for full queue.')
            pass
    else:
        try:
            await bot.change_presence(status=discord.Status.online,
                                      game=discord.Game(name='Sim: %s/%s' % (len(sims), server_opts['queue_limit'])))
        except:
            logger.warning('Failed to set presence for queue.')
            pass


async def check_spec(region, realm, char):
    global api_key
    url = "https://%s.api.battle.net/wow/character/%s/%s?fields=talents&locale=en_GB&apikey=%s" % (region, realm,
                                                                                                   quote(char), api_key)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            try:
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
            except:
                logger.critical('Error in aiohttp request: %s', url)
                return 'Failed to look up class spec from armory.'


async def data_sim():
    global api_key
    global waiting
    m_temp = ''
    while not waiting:
        waiting = True
        if sims[user]['data'] == 'addon':
            await set_status()
            msg = 'Please paste the output of your simulationcraft addon here and finish with DONE'
            await bot.send_message(sims[user]['message'].author, msg)
            addon_data = await bot.wait_for_message(author=sims[user]['message'].author, check=check, timeout=60)
            if addon_data is None:
                await bot.send_message(sims[user]['message'].author, 'No data given. Resetting session.')
                del sims[user]
                waiting = False
                await set_status()
                logger.info('No data was given to bot. Aborting sim.')
                return
            else:
                healing_roles = ['restoration', 'holy', 'discipline', 'mistweaver']
                sims[user]['addon'] = '%ssims/%s/%s-%s.simc' % (
                    htmldir, sims[user]['char'], sims[user]['char'], sims[user]['timestr'])
                f = open(sims[user]['addon'], 'w')
                f.write(addon_data.content[:-4])
                f.close()
                for crole in healing_roles:
                    crole = 'spec=' + crole
                    if crole in addon_data.content:
                        await bot.send_message(sims[user]['message'].channel,
                                               'SimulationCraft does not support healing.')
                        del sims[user]
                        waiting = False
                        await set_status()
                        logger.info('Character is a healer. Aborting sim.')
                        return

        if sims[user]['data'] != 'addon':
            api = await check_spec(sims[user]['region'], sims[user]['realm'].replace('_', '-'), sims[user]['char'])
            if api == 'HEALING':
                await bot.send_message(sims[user]['message'].channel, 'SimulationCraft does not support healing.')
                waiting = False
                del sims[user]
                logger.info('Character is a healer. Aborting sim.')
                return
            elif not api == 'DPS' and not api == 'TANK':
                msg = 'Something went wrong: %s' % api
                await bot.send_message(sims[user]['message'].channel, msg)
                waiting = False
                del sims[user]
                logger.warning('Simulation could not start: %s' % api)
                return
        for item in simc_opts['fightstyles']:
            if item.lower() == sims[user]['fightstyle'].lower():
                m_temp = m_temp + '**__' + item + '__**, '
            else:
                m_temp = m_temp + item + ', '
        for key in sims[user]:
            if key == 'movements':
                sims[user]['movements'] = m_temp
        if busy:
            position = len(sims) - 1
            await bot.send_message(sims[user]['message'].channel,
                                   'Simulation added to queue. Queue position: %s' % position)
            await set_status()
            logger.info('A new simulation has been added to queue')
        bot.loop.create_task(sim())

async def sim():
    global sims
    global busy
    global waiting
    waiting = False
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
            options += ' input=%s' % sims[sim_user]['addon']
        else:
            options += ' armory=%s,%s,%s' % (
                                             sims[sim_user]['region'], sims[sim_user]['realm'].replace('_', '-'),
                                             sims[sim_user]['char'])

        if sims[sim_user]['l_fixed'] == 1:
            options += ' vary_combat_length=0.0 fixed_time=1'
        await set_status()
        command = "%s %s" % (simc_opts['executable'], options)
        stout = open(os.path.join(htmldir, 'debug', 'simc.stout'), "w")
        sterr = open(os.path.join(htmldir, 'debug', 'simc.sterr'), "w")
        try:
            process = subprocess.Popen(command.split(" "), universal_newlines=True, stdout=stout, stderr=sterr)
            logger.info('----------------------------------')
            logger.info('%s started a simulation:' % sims[sim_user]['message'].author)
            logger.info('Character: ' + sims[sim_user]['char'].capitalize())
            logger.info('Realm: ' + sims[sim_user]['realm'].title().replace('_', ' '))
            logger.info('Fightstyle: ' + sims[sim_user]['movements'][
                                         sims[sim_user]['movements'].find("**__") + 4:sims[sim_user]['movements'].find(
                                             "__**")])
            logger.info('Fight Length: ' + str(sims[sim_user]['length']))
            logger.info('AOE: ' + sims[sim_user]['aoe'])
            logger.info('Iterations: ' + sims[sim_user]['iterations'])
            logger.info('Scaling: ' + sims[sim_user]['scaling'].capitalize())
            logger.info('Data: ' + sims[sim_user]['data'].capitalize())
            logger.info('----------------------------------')
        except FileNotFoundError as e:
            await bot.send_message(sims[sim_user]['message'].channel, 'ERR: Simulation could not start.')
            logger.critical('Bot could not start simulationcraft program. (ERR: %s)' % e)
            del sims[sim_user]
            await set_status()
            busy = False
            return
        msg = 'Realm: %s\nCharacter: %s\nFightstyle: %s\nFight Length: %s\nAoE: %s\n' \
              'Iterations: %s\nScaling: %s\nData: %s' % (
                  sims[sim_user]['realm'].title().replace('_', ' '), sims[sim_user]['char'].capitalize(),
                  sims[sim_user]['movements'],
                  sims[sim_user]['length'], sims[sim_user]['aoe'].capitalize(), sims[sim_user]['iterations'],
                  sims[sim_user]['scaling'].capitalize(), sims[sim_user]['data'].capitalize())
        await bot.send_message(sims[sim_user]['message'].channel, '\nSimulationCraft:\n' + msg)
        load = await bot.send_message(sims[sim_user]['message'].channel, 'Simulating: Starting...')
        await asyncio.sleep(1)
        while loop:
            await asyncio.sleep(1)
            with open(os.path.join(htmldir, 'debug', 'simc.stout'), errors='replace') as p:
                process_check = p.readlines()
            with open(os.path.join(htmldir, 'debug', 'simc.sterr'), errors='replace') as e:
                err_check = e.readlines()
            if len(err_check) > 0:
                print('test')
                if 'ERROR' in err_check[-1]:
                    await bot.edit_message(load, 'Simulation failed: ' + '\n'.join(err_check))
                    process.terminate()
                    del sims[sim_user]
                    await set_status()
                    logger.warning('Simulation failed: ' + '\n'.join(err_check))
                    loop = False
                    busy = False
                    print('test1')
                    if len(sims) == 0:
                        print('test2')
                        return
                    else:
                        print('test3')
                        bot.loop.create_task(sim())

            if len(process_check) > 1:
                if 'report took' in process_check[-2]:
                    loop = False
                    await bot.edit_message(load, 'Simulation done.')
                    await bot.send_message(sims[sim_user]['message'].channel,
                                           link + ' {0.author.mention}'.format(message))
                    process.terminate()
                    busy = False
                    del sims[sim_user]
                    await set_status()
                    logger.info('Simulation completed.')
                    if len(sims) != 0:
                        bot.loop.create_task(sim())
                    else:
                        busy = False
                        return
                else:
                    if 'Generating' in process_check[-1]:
                        done = '█' * (20 - process_check[-1].count('.'))
                        missing = '░' * (process_check[-1].count('.'))
                        progressbar = done + missing
                        percentage = 100 - process_check[-1].count('.') * 5
                        try:
                            load = await bot.edit_message(load, process_check[-1].split()[1] + ' ' + progressbar + ' ' +
                                                          str(percentage) + '%')
                        except:
                            logger.warning('Failed updating progress')
                            pass


def check(addon_data):
    return addon_data.content.endswith('DONE')


@bot.event
async def on_message(message):
    global busy
    global user
    global sims
    global api_key
    global waiting
    a_temp = ''
    channel = bot.get_channel(server_opts['channelid'])
    timestr = datetime.utcnow().strftime('%Y%m%d.%H%m%S%f')[:-3]
    args = message.content.lower()
    if message.author == bot.user:
        return
    if message.server is None:
        logger.info('%s sent follow data to bot: %s' % (message.author, message.content))
    elif args.startswith('!simc'):
        args = args.split(' -')
        if args:
            try:
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
                            logger.info('Sim could not be started because queue is full.')
                            return
                        if waiting:
                            await bot.send_message(sims[user]['message'].channel,
                                                   '**Waiting for simc addon data from %s.**' %
                                                   sims[user]['message'].author.display_name)
                            logger.info('Failed starting sim. Still waiting on data from previous sim')
                            return
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
                                       'addon': '',
                                       'fightstyle': simc_opts['fightstyles'][0],
                                       'movements': '',
                                       'length': simc_opts['length'],
                                       'l_fixed': 0,
                                       'timestr': datetime.utcnow().strftime('%Y%m%d.%H%m%S%f')[:-3],
                                       'message': ''
                                       }
                                }
                    sims.update(user_sim)
                    for key in sims[user]:
                        if key == 'message':
                            sims[user]['message'] = message
                    for i in range(len(args)):
                        if args[i] != '!simc':
                            if args[i].startswith(('r ', 'realm ')):
                                temp = args[i].split()
                                for key in sims[user]:
                                    if key == 'realm':
                                        sims[user]['realm'] = "_".join(temp[1:])
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
                                    logger.info('%s tried using custom iterations while the option is disabled')
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
                                    logger.info(
                                        '%s tried starting sim with unknown fightstyle: %s' % (message.author, temp[1]))
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
                                await bot.send_message(message.channel,
                                                       'Unknown command. Use !simc -h/help for commands')
                                del sims[user]
                                logger.info('Unknown command given to bot.')
                                return
                    if sims[user]['char'] == '':
                        await bot.send_message(message.channel, 'Character name is needed')
                        del sims[user]
                        logger.info('No character name given. Aborting sim.')
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
                    bot.loop.create_task(data_sim())
            except IndexError as e:
                await bot.send_message(message.channel, 'Unknown command. Use !simc -h/help for commands')
                logger.info('No command given to bot.(ERR: %s)' %e)
                return


@bot.event
async def on_ready():
    logger.info('Logged in as')
    logger.info(bot.user.name)
    logger.info(bot.user.id)
    check_version()
    logger.info(check_simc())
    logger.info('--------------')
    await set_status()

bot.run(server_opts['token'])
