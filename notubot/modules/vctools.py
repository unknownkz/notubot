# NOTUBOT - UserBot
# Copyright (C) 2021 notudope
#
# This file is a part of < https://github.com/notudope/notubot/ >
# PLease read the GNU General Public License v3.0 in
# <https://www.github.com/notudope/notubot/blob/main/LICENSE/>.

import asyncio

from telethon.tl.functions.channels import GetFullChannelRequest, DeleteMessagesRequest
from telethon.tl.functions.phone import CreateGroupCallRequest, DiscardGroupCallRequest, InviteToGroupCallRequest

from notubot import CMD_HELP
from notubot.events import bot_cmd


def user_list(ls, n):
    for i in range(0, len(ls), n):
        yield ls[i : i + n]


@bot_cmd(outgoing=True, groups_only=True, admins_only=True, pattern=r"^\.startvc(?: |$)(.*)")
async def vcstart(event):
    opts = event.pattern_match.group(1).strip()
    args = opts.split(" ")

    silent = ["s", "silent"]
    stfu = True if args[0] in silent else False

    title = ""
    for i in args[1:]:
        title += i + " "
    if title == "":
        title = ""

    _group = await event.client(
        CreateGroupCallRequest(
            event.chat_id,
            title=title,
        )
    )

    if stfu is not True:
        await event.edit("`Memulai Obrolan Video...`")
        await asyncio.sleep(15)
    else:
        await event.delete()
        if _group is not None:
            if _group.updates[1].id is not None:
                await event.client(DeleteMessagesRequest(event.chat_id, [_group.updates[1].id]))


@bot_cmd(outgoing=True, groups_only=True, admins_only=True, pattern=r"^\.stopvc(?: |$)(.*)")
async def vcstop(event):
    opts = event.pattern_match.group(1).strip()
    silent = ["s", "silent"]
    stfu = True if opts in silent else False

    call = (await event.client(GetFullChannelRequest(event.chat.id))).full_chat.call
    _group = None
    if call:
        _group = await event.client(DiscardGroupCallRequest(call))

    if stfu is not True:
        await event.edit("`Obrolan Video dimatikan...`")
        await asyncio.sleep(5)
        await event.delete()
    else:
        await event.delete()
        if _group is not None:
            if _group.updates[1].id is not None:
                await event.client(DeleteMessagesRequest(event.chat_id, [_group.updates[1].id]))


@bot_cmd(outgoing=True, groups_only=True, admins_only=True, pattern=r"^\.vcinvite$")
async def vcinvite(event):
    ok = await event.edit("`Mengundang semua anggota grup ke Obrolan Video...`")
    users = []
    z = 0

    async for x in event.client.iter_participants(event.chat_id):
        if not x.bot:
            users.append(x.id)
    hmm = list(user_list(users, 6))

    call = (await event.client(GetFullChannelRequest(event.chat.id))).full_chat.call
    if call:
        for p in hmm:
            try:
                await event.client(InviteToGroupCallRequest(call=call, users=p))
                z += 6
            except BaseException:
                pass

    await ok.edit(f"`Diundang {z} anggota`")
    await asyncio.sleep(20)
    await event.delete()


CMD_HELP.update(
    {
        "vctools": [
            "VC Tools",
            " - `.startvc <silent/s> <judul obrolan>` : Memulai Obrolan Video.\n"
            " - `.stopvc <silent/s>` : Mematikan Obrolan Video.\n"
            " - `.vcinvite` : Mengundang semua anggota grup ke Obrolan Video.\n",
        ]
    }
)
