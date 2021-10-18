import asyncio

from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.phone import (
    CreateGroupCallRequest,
    DiscardGroupCallRequest,
    GetGroupCallRequest,
    InviteToGroupCallRequest,
)

from userbot import CMD_HELP
from userbot.events import register


def user_list(ls, n):
    for i in range(0, len(ls), n):
        yield ls[i : i + n]


@register(outgoing=True, groups_only=True, admins_only=True, pattern=r"^\.startvc$")
async def vcstart(event):
    await event.client(
        CreateGroupCallRequest(
            event.chat_id,
            title="",
        )
    )
    await event.edit("`Memulai Obrolan Video...`")
    await asyncio.sleep(15)
    await event.delete()


@register(outgoing=True, groups_only=True, admins_only=True, pattern=r"^\.stopvc$")
async def vcstop(event):
    call = (await event.client(GetFullChannelRequest(event.chat.id))).full_chat.call
    if call:
        await event.client(DiscardGroupCallRequest(call))

    await event.edit("`Obrolan Video dimatikan...`")
    await asyncio.sleep(5)
    await event.delete()


@register(outgoing=True, groups_only=True, admins_only=True, pattern=r"^\.vcinvite$")
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
        "vctools": ">`.startvc`"
        "\nUsage: Memulai Obrolan Video (admin)."
        "\n\n>`.stopvc`"
        "\nUsage: Mematikan Obrolan Video (admin)."
        "\n\n>`.vcinvite`"
        "\nUsage: Mengundang semua anggota grup ke Obrolan Video (admin)."
    }
)
