# A Red implementation for installing cogs, the simple way.
#
# Original cogs to be found at:
# https://github.com/Twentysix26/Red-DiscordBot/blob/develop/cogs/downloader.py
# https://github.com/orels1/Red-Portal-Cogs/blob/master/redportal/redportal.py
#
# Courtesy to:
# orels1
# Twentysix26
# tekulvw
# neonobjclash
# aikaterna


from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
from __main__ import send_cmd_help, set_cog
import os
from subprocess import run, PIPE
import shutil
from asyncio import as_completed
from setuptools import distutils
import discord
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from time import time
from importlib.util import find_spec
import aiohttp
from urllib.parse import quote


NUM_THREADS = 4
REPO_NONEX = 0x1
REPO_CLONE = 0x2
REPO_SAME = 0x4


class UpdateError(Exception):
    pass


class CloningError(UpdateError):
    pass


class RequirementFail(UpdateError):
    pass


class PaddoCogManager:
    """Cog downloader/installer."""

    def __init__(self, bot):
        self.bot = bot
        self.path = "data/downloader/"
        self.file_path = "data/downloader/repos.json"
        self.repos = dataIO.load_json(self.file_path)
        self.executor = ThreadPoolExecutor(NUM_THREADS)
        self._do_first_run()

    def save_repos(self):
        dataIO.save_json(self.file_path, self.repos)

    async def _search_redportal(self, context, cog, repo):
        data = None
        base_url = 'https://cogs.red/api/v1/cogs/search'
        limit = 100
        offset = 0
        querystring = 'limit={}&offset={}'.format(limit, offset)
        c = quote(cog)
        url = '{}/{}?{}'.format(base_url, quote(cog), querystring)

        async with aiohttp.get(url, headers={"User-Agent": "Sono-Bot"}) as response:
            data = await response.json()

        single = True
        cog_list = []
        if data is not None and not data['error'] and len(data['results']['list']) > 0:
            cogs = data['results']['list']
            if len(cogs) > 1:
                for cog in cogs:
                    if cog['name'] == quote(c):
                        if repo:
                            if repo.lower() == cog['repo']['name'].lower():
                                cog_list.append(cog)
                                return cog_list
                        else:
                            cog_list.append(cog)
                            single = False
                    else:
                        cog_list.append(cog)
                        single = False
                if not single:
                    return cog_list

            else:
                for cog in cogs:
                    if cog['name'] == quote(c):
                        cog_list.append(cog)
                        return cog_list
            return False
        else:
            await self.bot.say('{} doesn\'t seem to be in any repo. Are you sure you got it right?'.format(c))

    async def _repo_add(self, context, cog):
        repo_name = cog['repo']['name']
        repo_url = cog['links']['github']['repo']
        self.repos[repo_name] = {}
        self.repos[repo_name]['url'] = repo_url
        try:
            self.update_repo(repo_name)
        except CloningError as e:
            await self.bot.say('That repository link doesn\'t seem to be valid.')
            del self.repos[repo_name]
        self.populate_list(repo_name)
        self.save_repos()
        data = self.get_info_data(repo_name)
        if data:
            msg = data.get("INSTALL_MSG")
            if msg:
                await self.bot.say(msg[:2000])
        await self.bot.say('Repo \'{}\' added.'.format(repo_name))

    async def _cog_add(self, context, repo_name: str, cog: str):
        """Installs specified cog"""
        if repo_name not in self.repos:
            await self.bot.say("That repo doesn't exist.")
            return
        if cog not in self.repos[repo_name]:
            await self.bot.say("That cog isn't available from that repo.")
            return
        data = self.get_info_data(repo_name, cog)
        try:
            install_cog = await self.install(repo_name, cog, notify_reqs=True)
        except RequirementFail:
            await self.bot.say("That cog has requirements that I could not "
                               "install. Check the console for more "
                               "informations.")
            return
        if data is not None:
            install_msg = data.get("INSTALL_MSG", None)
            if install_msg:
                await self.bot.say(install_msg[:2000])
        if install_cog:
            await self.bot.say("Installation completed. Load it now? (yes/no)")
            answer = await self.bot.wait_for_message(timeout=15,
                                                     author=context.message.author)
            if answer is None:
                await self.bot.say("Ok then, you can load it with"
                                   " `{}load {}`".format(context.prefix, cog))
            elif answer.content.lower().strip() == "yes":
                set_cog("cogs." + cog, True)
                owner = self.bot.get_cog('Owner')
                await owner.load.callback(owner, module=cog)
            else:
                await self.bot.say("Ok then, you can load it with"
                                   " `{}load {}`".format(context.prefix, cog))
        elif install_cog is False:
            await self.bot.say("Invalid cog. Installation aborted.")
        else:
            await self.bot.say("That cog doesn't exist. Use cog list to see"
                               " the full list.")

    async def _cog_uninstall(self, context, repo_name, cog):
        """Uninstalls a cog"""
        if repo_name not in self.repos:
            await self.bot.say("That repo doesn't exist.")
            return
        if cog not in self.repos[repo_name]:
            await self.bot.say("That cog isn't available from that repo.")
            return
        set_cog("cogs." + cog, False)
        self.repos[repo_name][cog]['INSTALLED'] = False
        self.save_repos()
        owner = self.bot.get_cog('Owner')
        await owner.unload.callback(owner, module=cog)
        os.remove(os.path.join("cogs", cog + ".py"))
        await self.bot.say("Cog successfully uninstalled.")

    @commands.group(pass_context=True, name='pcm')
    @checks.is_owner()
    async def _pcm(self, context):
        """Paddo's Cog Manager"""
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @_pcm.command(pass_context=True, name='install')
    async def _install(self, context, cog: str, repo: str=None):
        """Install a cog. If there's a result with more than 1 cog, add the repo name after the cog name."""
        result = await self._search_redportal(context, cog, repo)
        if result:
            cog = [0]
            if len(result) > 1:
                description = '\a\n'
                for i, cog in enumerate(result, 1):
                    if i < 10:
                        description += '`{}`\t  **[{}](https://cogs.red{}) in [{}](https://cogs.red{}) [{}]**\n'.format(str(i), cog['name'], cog['links']['self'], cog['repo']['name'], cog['links']['repo'], cog['repo']['type'])
                    else:
                        description += '`{}`\t**{} in {} [{}]**\n'.format(str(i), cog['name'], cog['repo']['name'], cog['repo']['type'])
                embed = discord.Embed(title='I have found the following cogs', color=discord.Color.red(), description=description)
                embed.set_footer(text='To install: {}pcm install <cog> <repo>'.format(context.prefix))
                await self.bot.say(embed=embed)
            else:
                cog = result[0]
                if cog['repo']['name'] not in self.repos:
                    await self._repo_add(context, cog)
                await self._cog_add(context, cog['repo']['name'], cog['name'])

    @_pcm.command(pass_context=True, name='uninstall')
    async def _uninstall(self, context, cog: str):
        """Uninstall a cog"""
        for repo in self.repos:
            for repo_cog in self.repos[repo]:
                if repo_cog == cog.lower() and self.repos[repo][cog]['INSTALLED'] is not False:
                    await self._cog_uninstall(context, repo, cog)

    @_pcm.command(pass_context=True, name='search')
    async def _search(self, context, cog: str, repo: str=None):
        """Search for a cog. If there's a result with more than 1 cog, add the repo name after the cog name."""
        result = await self._search_redportal(context, cog, repo)
        print(result)
        if result:
            if len(result) > 1:
                description = '\a\n'
                for i, cog in enumerate(result, 1):
                    if i < 10:
                        description += '`{}`\t  **[{}](https://cogs.red{}) in [{}](https://cogs.red{}) [{}]**\n'.format(str(i), cog['name'], cog['links']['self'], cog['repo']['name'], cog['links']['repo'], cog['repo']['type'])
                    else:
                        description += '`{}`\t**{} in {} [{}]**\n'.format(str(i), cog['name'], cog['repo']['name'], cog['repo']['type'])
                embed = discord.Embed(title='I have found the following cogs', color=discord.Color.red(), description=description)
                embed.set_footer(text='To install: {}pcm install <cog> <repo>'.format(context.prefix))
            else:
                cog = result[0]

                embed = discord.Embed(title='{} by {}'.format(cog['name'].capitalize(), cog['author']['name']), url='https://cogs.red{}'.format(cog['links']['self']), description='\a\n'+(len(cog['description']) > 175 and '{}...'.format(cog['description'][:175]) or cog['description']) or cog['short'], color=discord.Color.red())
                embed.add_field(name='Type', value=cog['repo']['type'].capitalize(), inline=True)
                embed.add_field(name='Author', value=cog['author']['name'], inline=True)
                embed.add_field(name='Repo', value=cog['repo']['name'], inline=True)
                embed.add_field(name='Command to add cog', value='{}pcm install {}'.format(context.prefix, cog['name']), inline=False)
            await self.bot.say(embed=embed)

    @_pcm.command(pass_context=True, name='update')
    async def _update(self, context):
        """Update cogs"""
        tasknum = 0
        num_repos = len(self.repos)
        min_dt = 0.5
        burst_inc = 0.1/(NUM_THREADS)
        touch_n = tasknum
        touch_t = time()

        def regulate(touch_t, touch_n):
            dt = time() - touch_t
            if dt + burst_inc*(touch_n) > min_dt:
                touch_n = 0
                touch_t = time()
                return True, touch_t, touch_n
            return False, touch_t, touch_n + 1

        tasks = []
        for r in self.repos:
            task = partial(self.update_repo, r)
            task = self.bot.loop.run_in_executor(self.executor, task)
            tasks.append(task)
        base_msg = "Downloading updated cogs, please wait... "
        status = ' %d/%d repos updated' % (tasknum, num_repos)
        msg = await self.bot.say(base_msg + status)
        updated_cogs = []
        new_cogs = []
        deleted_cogs = []
        failed_cogs = []
        error_repos = {}
        installed_updated_cogs = []
        for f in as_completed(tasks):
            tasknum += 1
            try:
                name, updates, oldhash = await f
                if updates:
                    if type(updates) is dict:
                        for k, l in updates.items():
                            tl = [(name, c, oldhash) for c in l]
                            if k == 'A':
                                new_cogs.extend(tl)
                            elif k == 'D':
                                deleted_cogs.extend(tl)
                            elif k == 'M':
                                updated_cogs.extend(tl)
            except UpdateError as e:
                name, what = e.args
                error_repos[name] = what
            edit, touch_t, touch_n = regulate(touch_t, touch_n)
            if edit:
                status = ' %d/%d repos updated' % (tasknum, num_repos)
                msg = await self._robust_edit(msg, base_msg + status)
        status = 'done. '

        for t in updated_cogs:
            repo, cog, _ = t
            if self.repos[repo][cog]['INSTALLED']:
                try:
                    await self.install(repo, cog,
                                       no_install_on_reqs_fail=False)
                except RequirementFail:
                    failed_cogs.append(t)
                else:
                    installed_updated_cogs.append(t)

        for t in updated_cogs.copy():
            if t in failed_cogs:
                updated_cogs.remove(t)

        if not any(self.repos[repo][cog]['INSTALLED'] for
                   repo, cog, _ in updated_cogs):
            status += ' No updates to apply. '
        if new_cogs:
            status += '\nNew cogs: ' \
                   + ', '.join('%s/%s' % c[:2] for c in new_cogs) + '.'
        if deleted_cogs:
            status += '\nDeleted cogs: ' \
                   + ', '.join('%s/%s' % c[:2] for c in deleted_cogs) + '.'
        if updated_cogs:
            status += '\nUpdated cogs: ' \
                   + ', '.join('%s/%s' % c[:2] for c in updated_cogs) + '.'
        if failed_cogs:
            status += '\nCogs that got new requirements which have ' + \
                   'failed to install: ' + \
                   ', '.join('%s/%s' % c[:2] for c in failed_cogs) + '.'
        if error_repos:
            status += '\nThe following repos failed to update: '
            for n, what in error_repos.items():
                status += '\n%s: %s' % (n, what)
        msg = await self._robust_edit(msg, base_msg + status)
        if not installed_updated_cogs:
            return
        await self.bot.say("Cogs updated. Reload updated cogs? (yes/no)")
        answer = await self.bot.wait_for_message(timeout=15,
                                                 author=context.message.author)
        if answer is None:
            await self.bot.say("Ok then, you can reload cogs with"
                               " `{}reload <cog_name>`".format(context.prefix))
        elif answer.content.lower().strip() == "yes":
            registry = dataIO.load_json("data/red/cogs.json")
            update_list = []
            fail_list = []
            for repo, cog, _ in installed_updated_cogs:
                if not registry.get('cogs.' + cog, False):
                    continue
                try:
                    self.bot.unload_extension("cogs." + cog)
                    self.bot.load_extension("cogs." + cog)
                    update_list.append(cog)
                except:
                    fail_list.append(cog)
            msg = 'Done.'
            if update_list:
                msg += " The following cogs were reloaded: "\
                    + ', '.join(update_list) + "\n"
            if fail_list:
                msg += " The following cogs failed to reload: "\
                    + ', '.join(fail_list)
            await self.bot.say(msg)

        else:
            await self.bot.say("Ok then, you can reload cogs with"
                               " `{}reload <cog_name>`".format(context.prefix))

    async def install(self, repo_name, cog, *, notify_reqs=False,
                      no_install_on_reqs_fail=True):
        # 'no_install_on_reqs_fail' will make the cog get installed anyway
        # on requirements installation fail. This is necessary because due to
        # how 'cog update' works right now, the user would have no way to
        # reupdate the cog if the update fails, since 'cog update' only
        # updates the cogs that get a new commit.
        # This is not a great way to deal with the problem and a cog update
        # rework would probably be the best course of action.
        reqs_failed = False
        if cog.endswith('.py'):
            cog = cog[:-3]
        path = self.repos[repo_name][cog]['file']
        cog_folder_path = self.repos[repo_name][cog]['folder']
        cog_data_path = os.path.join(cog_folder_path, 'data')
        data = self.get_info_data(repo_name, cog)
        if data is not None:
            requirements = data.get("REQUIREMENTS", [])
            requirements = [r for r in requirements
                            if not self.is_lib_installed(r)]
            if requirements and notify_reqs:
                await self.bot.say("Installing cog's requirements...")
            for requirement in requirements:
                if not self.is_lib_installed(requirement):
                    success = await self.bot.pip_install(requirement)
                    if not success:
                        if no_install_on_reqs_fail:
                            raise RequirementFail()
                        else:
                            reqs_failed = True
        to_path = os.path.join("cogs/", cog + ".py")
        print("Copying {}...".format(cog))
        shutil.copy(path, to_path)
        if os.path.exists(cog_data_path):
            print("Copying {}'s data folder...".format(cog))
            distutils.dir_util.copy_tree(cog_data_path,
                                         os.path.join('data/', cog))
        self.repos[repo_name][cog]['INSTALLED'] = True
        self.save_repos()
        if not reqs_failed:
            return True
        else:
            raise RequirementFail()

    def get_info_data(self, repo_name, cog=None):
        if cog is not None:
            cogs = self.list_cogs(repo_name)
            if cog in cogs:
                info_file = os.path.join(cogs[cog].get('folder'), "info.json")
                if os.path.isfile(info_file):
                    try:
                        data = dataIO.load_json(info_file)
                    except:
                        return None
                    return data
        else:
            repo_info = os.path.join(self.path, repo_name, 'info.json')
            if os.path.isfile(repo_info):
                try:
                    data = dataIO.load_json(repo_info)
                    return data
                except:
                    return None
        return None

    def list_cogs(self, repo_name):
        valid_cogs = {}
        repo_path = os.path.join(self.path, repo_name)
        folders = [f for f in os.listdir(repo_path)
                   if os.path.isdir(os.path.join(repo_path, f))]
        legacy_path = os.path.join(repo_path, "cogs")
        legacy_folders = []
        if os.path.exists(legacy_path):
            for f in os.listdir(legacy_path):
                if os.path.isdir(os.path.join(legacy_path, f)):
                    legacy_folders.append(os.path.join("cogs", f))
        folders = folders + legacy_folders
        for f in folders:
            cog_folder_path = os.path.join(self.path, repo_name, f)
            cog_folder = os.path.basename(cog_folder_path)
            for cog in os.listdir(cog_folder_path):
                cog_path = os.path.join(cog_folder_path, cog)
                if os.path.isfile(cog_path) and cog_folder == cog[:-3]:
                    valid_cogs[cog[:-3]] = {'folder': cog_folder_path,
                                            'file': cog_path}
        return valid_cogs

    def is_lib_installed(self, name):
        return bool(find_spec(name))

    def _do_first_run(self):
        invalid = []
        save = False

        for repo in self.repos:
            broken = 'url' in self.repos[repo] and len(self.repos[repo]) == 1
            if broken:
                save = True
                try:
                    self.update_repo(repo)
                    self.populate_list(repo)
                except CloningError:
                    invalid.append(repo)
                    continue
                except Exception as e:
                    print(e)  # TODO: Proper logging
                    continue

        for repo in invalid:
            del self.repos[repo]
        if save:
            self.save_repos()

    def populate_list(self, name):
        valid_cogs = self.list_cogs(name)
        new = set(valid_cogs.keys())
        old = set(self.repos[name].keys())
        for cog in new - old:
            self.repos[name][cog] = valid_cogs.get(cog, {})
            self.repos[name][cog]['INSTALLED'] = False
        for cog in new & old:
            self.repos[name][cog].update(valid_cogs[cog])
        for cog in old - new:
            if cog != 'url':
                del self.repos[name][cog]

    def update_repo(self, name):
        try:
            dd = self.path
            if name not in self.repos:
                raise UpdateError("Repo does not exist in data, wtf")
            folder = os.path.join(dd, name)
            if not os.path.exists(os.path.join(folder, '.git')):
                url = self.repos[name].get('url')
                if not url:
                    raise UpdateError("Need to clone but no URL set")
                branch = None
                if "@" in url:  # Specific branch
                    url, branch = url.rsplit("@", maxsplit=1)
                if branch is None:
                    p = run(["git", "clone", url, dd + name])
                else:
                    p = run(["git", "clone", "-b", branch, url, dd + name])
                if p.returncode != 0:
                    raise CloningError()
                self.populate_list(name)
                return name, REPO_CLONE, None
            else:
                rpcmd = ["git", "-C", dd + name, "rev-parse", "HEAD"]
                p = run(["git", "-C", dd + name, "reset", "--hard",
                        "origin/HEAD", "-q"])
                if p.returncode != 0:
                    raise UpdateError("Error resetting to origin/HEAD")
                p = run(rpcmd, stdout=PIPE)
                if p.returncode != 0:
                    raise UpdateError("Unable to determine old commit hash")
                oldhash = p.stdout.decode().strip()
                p = run(["git", "-C", dd + name, "pull", "-q", "--ff-only"])
                if p.returncode != 0:
                    raise UpdateError("Error pulling updates")
                p = run(rpcmd, stdout=PIPE)
                if p.returncode != 0:
                    raise UpdateError("Unable to determine new commit hash")
                newhash = p.stdout.decode().strip()
                if oldhash == newhash:
                    return name, REPO_SAME, None
                else:
                    self.populate_list(name)
                    self.save_repos()
                    ret = {}
                    cmd = ['git', '-C', dd + name, 'diff', '--no-commit-id',
                           '--name-status', oldhash, newhash]
                    p = run(cmd, stdout=PIPE)
                    if p.returncode != 0:
                        raise UpdateError("Error in git diff")
                    changed = p.stdout.strip().decode().split('\n')
                    for f in changed:
                        if not f.endswith('.py'):
                            continue
                        status, cogpath = f.split('\t')
                        cogname = os.path.split(cogpath)[-1][:-3]  # strip .py
                        if status not in ret:
                            ret[status] = []
                        ret[status].append(cogname)
                    return name, ret, oldhash
        except CloningError as e:
            raise CloningError(name, *e.args) from None
        except UpdateError as e:
            raise UpdateError(name, *e.args) from None

    async def _robust_edit(self, msg, text):
        try:
            msg = await self.bot.edit_message(msg, text)
        except discord.errors.NotFound:
            msg = await self.bot.send_message(msg.channel, text)
        except:
            raise
        return msg


def check_folders():
    if not os.path.exists("data/downloader"):
        print('Making repo downloads folder...')
        os.mkdir('data/downloader')


def check_files():
    f = "data/downloader/repos.json"
    if not dataIO.is_valid_json(f):
        print("Creating default data/downloader/repos.json")
        dataIO.save_json(f, {})


def setup(bot):
    check_folders()
    check_files()
    n = PaddoCogManager(bot)
    bot.add_cog(n)
