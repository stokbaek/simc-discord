# simc-discord
SimulationCraft Bot for discord.

The following things are needed to run the bot:
* Python 3.5+
* Flask 0.12+: http://flask.pocoo.org/
* Python Discord lib: https://github.com/Rapptz/discord.py
* Webservice on the server to hand out a link to the finished simulation.
* A working version of simulationcraft TCI
* Blizzard API key (This is needed to use armory): Keys needs to be added in user_data and it can be generated here: https://dev.battle.net

Tested systems:
- [x] Debian 8
- [x] Ubuntu 16.04
- [x] RHEL 7
- [x] Windows Server 2016
- [ ] ~~FreeBSD 11.0~~ *SimulationCraft does not build well on FreeBSD*

The output from simulationcraft can be found: `<WEBSITE>/debug/simc.sterr or simc.stout`. These files are live updated during a simulation.

Setting the `executable` in the `user_data.json` for Windows can be abit tricky.

Here is an example on how it can be done:

`"executable": "START /B C:\\Simulationcraft^(x64^)\\710-03\\simc.exe",`
* `START` makes it run in the background, this is needed to give a progress bar in discord
* `/B` allows output to be written to file
* `^` is windows way to escape a character. If `( )` is not escaped will it fail because it cannot find path

***Help for simulation through Discord:***

*Options:*
```
-c  -character    in-game name
-r  -realm        realm name
-s  -scale        yes/no
-d  -data         armory/addon
-f  -fightstyle   Choose between different fightstyles
-l  -length       Choose fight length in seconds
-a  -aoe          yes/no
    -ptr          Enables PTR build on sim
-v  -version      Gives the version of simulationcraft being used
```
* Simulate using armory with stat scaling:

`!simc -character NAME -scale yes`
* Simulate using addon without stat scaling:

`!simc -character NAME -d addon`

*The bot will whisper asking for a paste of data string from the addon ingame. The last line should contain DONE.*

Addon can be found here: <https://mods.curse.com/addons/wow/simulationcraft>

example
```
warlock="Stokbaek"
level=110
race=goblin
region=eu
server=magtheridon
role=attack
professions=alchemy=784/herbalism=800
talents=1131323
spec=destruction
artifact=38:0:0:0:0:803:1:807:3:808:2:809:3:810:3:811:3:812:3:814:1:815:1:817:1:818:1:1355:1
head=,id=139909,bonus_id=665
neck=,id=139332,enchant_id=5439,bonus_id=1807/1808/1472
shoulder=,id=134221,bonus_id=3416/1532/3336
back=,id=139248,bonus_id=1805/1808/1492/3336
chest=,id=142410,bonus_id=3468/1808/1492
wrist=,id=142415,bonus_id=3467/1497/3337
hands=,id=140993,bonus_id=1805/1487
waist=,id=142153,bonus_id=3452/1487/3337
legs=,id=139190,bonus_id=1805/1487
feet=,id=134308,bonus_id=3415/1522/3336
finger1=,id=132452,enchant_id=5428,bonus_id=3459/3458
finger2=,id=142520,enchant_id=5428,bonus_id=3467/1492/3337
trinket1=,id=137301,bonus_id=3509/1532/3336
trinket2=,id=142157,bonus_id=41/3453/1472
main_hand=,id=128941,bonus_id=749,relic_id=3506:1482/3467:1477/3453:1472,gem_id=0/0/0/0
DONE
```
