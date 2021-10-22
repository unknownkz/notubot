# NOTUBOT - UserBot
# Copyright (C) 2021 notudope
#
# This file is a part of < https://github.com/notudope/notubot/ >
# PLease read the GNU General Public License v3.0 in
# <https://www.github.com/notudope/notubot/blob/main/LICENSE/>.

import asyncio
import sys
from os import (
    environ,
    execle,
    remove,
    path,
)

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError, NoSuchPathError

from notubot import (
    BOTLOG,
    BOTLOG_CHATID,
    CMD_HELP,
    HEROKU_API_KEY,
    HEROKU_APP_NAME,
    UPSTREAM_REPO_BRANCH,
    UPSTREAM_REPO_URL,
    BOT_NAME,
)
from notubot.events import bot_cmd

requirements_path = path.join(path.dirname(path.dirname(path.dirname(__file__))), "requirements.txt")


async def update_requirements():
    reqs = str(requirements_path)
    try:
        process = await asyncio.create_subprocess_shell(
            " ".join([sys.executable, "-m", "pip", "install", "-r", reqs]),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await process.communicate()
        return process.returncode
    except Exception as e:
        return repr(e)


async def gen_chlog(repo, diff):
    ch_log = ""
    d_form = "%d/%m/%y"
    for c in repo.iter_commits(diff):
        ch_log += f"•[{c.committed_datetime.strftime(d_form)}]: " f"{c.summary} <{c.author}>\n"
    return ch_log


async def print_changelogs(event, ac_br, changelog):
    changelog_str = f"`{BOT_NAME}` **Pembaruan Tersedia Untuk [{ac_br}]:\n\nCHANGELOG:**\n`{changelog}`"

    if len(changelog_str) > 4096:
        await event.edit("`Data CHANGELOG terlalu besar, buka file untuk melihatnya.`")
        file = open("output.txt", "w+")
        file.write(changelog_str)
        file.close()

        await event.client.send_file(
            event.chat_id,
            "output.txt",
            reply_to=event.id,
        )
        remove("output.txt")
    else:
        await event.client.send_message(
            event.chat_id,
            changelog_str,
            reply_to=event.id,
        )
    return True


async def deploy(event, repo, ups_rem, ac_br, txt):
    if HEROKU_API_KEY is not None:
        import heroku3

        heroku = heroku3.from_key(HEROKU_API_KEY)
        heroku_app = None
        heroku_applications = heroku.apps()

        if HEROKU_APP_NAME is None:
            await event.edit(
                f"Harap **tentukan variabel** `HEROKU_APP_NAME` untuk dapat Deploy perubahan terbaru dari `{BOT_NAME}`."
            )
            repo.__del__()
            return

        for app in heroku_applications:
            if app.name == HEROKU_APP_NAME:
                heroku_app = app
                break

        if heroku_app is None:
            await event.edit(f"{txt}\n" "`Kredensial Heroku tidak valid untuk deploy UserBot dyno.`")
            return repo.__del__()

        await event.edit(f"`{BOT_NAME} dyno sedang memperbarui, perkiraan waktu 2-7 menit...`")

        try:
            from notubot.modules.sql_helper.globals import addgvar, delgvar

            delgvar("restartstatus")
            addgvar("restartstatus", f"{event.chat_id}\n{event.id}")
        except AttributeError:
            pass

        ups_rem.fetch(ac_br)
        repo.git.reset("--hard", "FETCH_HEAD")
        heroku_git_url = heroku_app.git_url.replace("https://", "https://api:" + HEROKU_API_KEY + "@")
        if "heroku" in repo.remotes:
            remote = repo.remote("heroku")
            remote.set_url(heroku_git_url)
        else:
            remote = repo.create_remote("heroku", heroku_git_url)

        try:
            remote.push(refspec="HEAD:refs/heads/master", force=True)
        except Exception as error:
            await event.edit(f"{txt}\n`Disini catatan kesalahan:\n{error}`")
            return repo.__del__()

        build = heroku_app.builds(order_by="created_at", sort="desc")[0]

        if build.status == "failed":
            await event.edit("`Build gagal!\n" "Dibatalkan atau ada beberapa kesalahan...`")
            await asyncio.sleep(5)
            return await event.delete()
        else:
            await event.edit(f"`{BOT_NAME} Berhasil Diperbarui, Dimuat Ulang...`")
            if BOTLOG:
                await event.client.send_message(BOTLOG_CHATID, "#bot #push \n" f"**{BOT_NAME} Berhasil Diperbarui ツ**")

    else:
        await event.edit("Harap **tentukan variabel** `HEROKU_API_KEY`.")
    return


async def update(event, repo, ups_rem, ac_br):
    try:
        ups_rem.pull(ac_br)
    except GitCommandError:
        repo.git.reset("--hard", "FETCH_HEAD")

    await update_requirements()
    await event.edit(f"**{BOT_NAME}** `Berhasil Diperbarui!`")
    await asyncio.sleep(1)
    await event.edit(f"**{BOT_NAME}** `Dimuat Ulang...`")
    await asyncio.sleep(1)
    await event.edit(f"**{BOT_NAME}** `Tunggu Beberapa Detik Dan Cobalah...`")

    if BOTLOG:
        await event.client.send_message(BOTLOG_CHATID, "#bot #pull \n" f"**{BOT_NAME} Telah Diperbarui ツ**")

    try:
        from notubot.modules.sql_helper.globals import addgvar, delgvar

        delgvar("restartstatus")
        addgvar("restartstatus", f"{event.chat_id}\n{event.id}")
    except AttributeError:
        pass

    args = [sys.executable, "-m", "notubot"]
    execle(sys.executable, *args, environ)


@bot_cmd(outgoing=True, pattern=r"^.update(?: |$)(now|deploy|pull|push|one|all)?")
async def upstream(event):
    "For .update command, check if the bot is up to date, update if specified"
    opts = event.pattern_match.group(1)
    off_repo = UPSTREAM_REPO_URL
    force_update = False

    await event.edit("`...`")
    try:
        txt = "`Oops.. Pembaruan tidak dapat dilanjutkan karena "
        txt += "Beberapa masalah terjadi`\n\n**LOGTRACE:**\n"
        repo = Repo()
    except NoSuchPathError as error:
        await event.edit(f"{txt}\n`Direktori {error} tidak ditemukan.`")
        return repo.__del__()
    except GitCommandError as error:
        await event.edit(f"{txt}\n`Kesalahan diawal! {error}`")
        return repo.__del__()
    except InvalidGitRepositoryError as error:
        if opts is None:
            return await event.edit(
                f"`Direktori {error} "
                "sepertinya bukan repositori git.\n"
                "Tapi bisa memperbaiki dengan memperbarui paksa UserBot menggunakan "
                ".update now|pull|one.`"
            )
        repo = Repo.init()
        origin = repo.create_remote("upstream", off_repo)
        origin.fetch()
        force_update = True
        repo.create_head("master", origin.refs.master)
        repo.heads.master.set_tracking_branch(origin.refs.master)
        repo.heads.master.checkout(True)

    ac_br = repo.active_branch.name
    if ac_br != UPSTREAM_REPO_BRANCH:
        await event.edit(
            "**[UPDATER]:**\n"
            f"`Sepertinya menggunakan custom branch ({ac_br}). "
            "Dalam hal ini, Updater tidak dapat mengidentifikasi "
            "branch mana yang akan digabung. "
            "Silakan gunakan official branch.`"
        )
        return repo.__del__()
    try:
        repo.create_remote("upstream", off_repo)
    except BaseException:
        pass

    ups_rem = repo.remote("upstream")
    ups_rem.fetch(ac_br)

    changelog = await gen_chlog(repo, f"HEAD..upstream/{ac_br}")

    if opts == "deploy" or opts == "push" or opts == "all":
        await event.edit(f"`Proses Deploy {BOT_NAME} Harap Tunggu...`")
        await deploy(event, repo, ups_rem, ac_br, txt)

    if changelog == "" and force_update is False:
        await event.edit(f"\n`{BOT_NAME}`  **up-to-date** branch " f"`{UPSTREAM_REPO_BRANCH}`\n")
        return repo.__del__()

    if opts is None and force_update is False:
        await print_changelogs(event, ac_br, changelog)
        await event.delete()
        await event.respond("Jalankan `.update now|pull|one` untuk __memperbarui sementara__.")
        await event.respond("Jalankan `.update deploy|push|all` untuk __memperbarui permanen__.")
        return

    if force_update:
        await event.edit("`Memaksa sinkronisasi ke kode UserBot stabil terbaru, harap tunggu...`")
    else:
        await event.edit(f"`Proses Update {BOT_NAME} Loading....1%`")
        await event.edit(f"`Proses Update {BOT_NAME} Loading....20%`")
        await event.edit(f"`Proses Update {BOT_NAME} Loading....35%`")
        await event.edit(f"`Proses Update {BOT_NAME} Loading....77%`")
        await event.edit(f"`Proses Update {BOT_NAME} Updating...90%`")
        await event.edit(f"`Proses Update {BOT_NAME} Mohon Tunggu Sebentar...100%`")

    if opts == "now" or opts == "pull" or opts == "one":
        await event.edit(f"`Memperbarui {BOT_NAME} Harap Tunggu...`")
        await update(event, repo, ups_rem, ac_br)
    return


@bot_cmd(outgoing=True, pattern=r"^\.repo$")
async def repo(event):
    """For .repo command, just returns the repo URL."""
    await event.edit(f"📦 **[Disini REPO](https://github.com/notudope/notubot)** `{BOT_NAME}`", link_preview=False)


CMD_HELP.update(
    {
        "update": [
            "Update",
            " - `.update` : Mengecek apakah ada pembaruan pada repo UserBot termasuk menampilkan changelog.\n"
            " - `.update now|pull|one` : Memperbarui sistem UserBot jika ada pembaruan pada repo UserBot.\n"
            " - `.update deploy|push|all` : Deploy UserBot (heroku), ini akan memaksa deploy meskipun tidak ada pembaruan pada UserBot.\n"
            " - `.repo` : Github Repository UserBot.\n",
        ]
    }
)