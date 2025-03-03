import random
import string

from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, Message

import config
from config import BANNED_USERS, lyrical
from BADMUSIC import app, LOGGER, Platform
from BADMUSIC.utils import seconds_to_min, time_to_seconds
from BADMUSIC.utils.database import is_video_allowed, is_served_user
from BADMUSIC.utils.decorators.play import PlayWrapper
from BADMUSIC.utils.formatters import formats
from BADMUSIC.utils.inline.play import (
    livestream_markup,
    playlist_markup,
    slider_markup,
    track_markup,
)
from BADMUSIC.utils.inline.playlist import botplaylist_markup
from BADMUSIC.utils.logger import play_logs
from BADMUSIC.utils.stream.stream import stream
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ChatMemberUpdated
from pyrogram.errors import UserNotParticipant, ChatAdminRequired, FloodWait, UserAlreadyParticipant
from pyrogram.enums import ChatMemberStatus
from BADMUSIC import app

# Command
# PLAY_COMMAND = get_command("PLAY_COMMAND")

# The username and ID of the channel (not the ID)
CHANNEL_USERNAME = 'HEROKUBIN_01'  # Replace with your channel's username
CHANNEL_ID = -1002020205239  # Replace with your channel's chat ID (to access programmatically)

# Function to check if the bot is a member of the channel
async def check_bot_in_channel():
    try:
        # Check if the bot is a member of the channel
        bot_member = await app.get_chat_member(CHANNEL_USERNAME, app.me.id)
        return bot_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except UserNotParticipant:
        return False

# Function to check if a user is a member of the channel
async def check_channel_membership(user_id):
    try:
        member = await app.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]
    except UserNotParticipant:
        return False

# Event to handle user joining or leaving the channel
@app.on_chat_member_updated()
async def monitor_member_update(client: Client, member: ChatMemberUpdated):
    if member.chat.username == CHANNEL_USERNAME:
        if member.new_chat_member and member.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
            user_id = member.new_chat_member.user.id
            # You can add actions like sending a welcome message if necessary
        elif member.left_chat_member:
            user_id = member.left_chat_member.user.id
            # Perform actions like notifying if needed

# Function to create an inline button for joining the channel
def inline_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")],
    ])

# Wrapper for the play command
@app.on_message(
    filters.command(
        [
            "play",
            "vplay",
            "cplay",
            "cvplay",
            "playforce",
            "vplayforce",
            "cplayforce",
            "cvplayforce",
        ],
        prefixes=["/", "!", "%", ",", "@", "#"],
    )
    & filters.group
    & ~BANNED_USERS
)
@PlayWrapper
async def play_commnd(
    client,
    message: Message,
    _,
    chat_id,
    video,
    channel,
    playmode,
    url,
    fplay,
):
    user_id = message.from_user.id

    # Check if the user is a verified user
    if not await is_served_user(user_id):
        await message.reply_text(
            text="Error, You're Not A Verified User ❌\nPlease Click On The Below Button To Verify Yourself .",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="Click For Play Or Verify Here",
                            url=f"https://t.me/{app.username}?start=verify",
                        )
                    ]
                ]
            ),
        )
        return

    # Check if the bot is in the channel
    if not await check_bot_in_channel():
        await message.reply_text(
            "The bot is not a member of the required channel. Please ensure that the bot is added to the channel and has access to operate.",
            reply_markup=inline_button()
        )
        return
    
    # Check if the user is a member of the channel
    if not await check_channel_membership(user_id):
        await message.reply_text(
            "You need to join our channel to proceed. Please click the button below to join.",
            reply_markup=inline_button()
        )
        return

    # Proceed with the play command logic if the user is verified and a channel member
    # Add your existing play logic here
    # Example: Send a confirmation or play the video.
    # await message.reply_text("Now playing the video...")

    mystic = await message.reply_text(
        _["play_2"].format(channel) if channel else _["play_1"]
    )
    plist_id = None
    slider = None
    plist_type = None
    spotify = None
    user_id = message.from_user.id
    user_name = message.from_user.mention
    audio_telegram = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    video_telegram = (
        (message.reply_to_message.video or message.reply_to_message.document)
        if message.reply_to_message
        else None
    )
    if audio_telegram:
        if audio_telegram.file_size > config.TG_AUDIO_FILESIZE_LIMIT:
            return await mystic.edit_text(_["play_5"])
        duration_min = seconds_to_min(audio_telegram.duration)
        if (audio_telegram.duration) > config.DURATION_LIMIT:
            return await mystic.edit_text(
                _["play_6"].format(config.DURATION_LIMIT_MIN, duration_min)
            )
        file_path = await Platform.telegram.get_filepath(audio=audio_telegram)
        if await Platform.telegram.download(_, message, mystic, file_path):
            message_link = await Platform.telegram.get_link(message)
            file_name = await Platform.telegram.get_filename(audio_telegram, audio=True)
            dur = await Platform.telegram.get_duration(audio_telegram)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }

            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="telegram",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    err = _["general_3"].format(ex_type)
                    LOGGER(__name__).error("An error occurred", exc_info=True)
                return await mystic.edit_text(err)
            return await mystic.delete()
        return
    elif video_telegram:
        if not await is_video_allowed(message.chat.id):
            return await mystic.edit_text(_["play_3"])
        if message.reply_to_message.document:
            try:
                ext = video_telegram.file_name.split(".")[-1]
                if ext.lower() not in formats:
                    return await mystic.edit_text(
                        _["play_8"].format(f"{' | '.join(formats)}")
                    )
            except Exception:
                return await mystic.edit_text(
                    _["play_8"].format(f"{' | '.join(formats)}")
                )
        if video_telegram.file_size > config.TG_VIDEO_FILESIZE_LIMIT:
            return await mystic.edit_text(_["play_9"])
        file_path = await Platform.telegram.get_filepath(video=video_telegram)
        if await Platform.telegram.download(_, message, mystic, file_path):
            message_link = await Platform.telegram.get_link(message)
            file_name = await Platform.telegram.get_filename(video_telegram)
            dur = await Platform.telegram.get_duration(video_telegram)
            details = {
                "title": file_name,
                "link": message_link,
                "path": file_path,
                "dur": dur,
            }
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    video=True,
                    streamtype="telegram",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    LOGGER(__name__).error("An error occurred", exc_info=True)
                    err = _["general_3"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
        return
    elif url:
        if await Platform.youtube.exists(url):
            if "playlist" in url:
                try:
                    details = await Platform.youtube.playlist(
                        url,
                        config.PLAYLIST_FETCH_LIMIT,
                    )
                except Exception as e:
                    print(e)
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "yt"
                if "&" in url:
                    plist_id = (url.split("=")[1]).split("&")[0]
                else:
                    plist_id = url.split("=")[1]
                img = config.PLAYLIST_IMG_URL
                cap = _["play_10"]
            elif "https://youtu.be" in url:
                videoid = url.split("/")[-1].split("?")[0]
                details, track_id = await Platform.youtube.track(
                    f"https://www.youtube.com/watch?v={videoid}"
                )
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_11"].format(
                    details["title"],
                    details["duration_min"],
                )
            else:
                try:
                    details, track_id = await Platform.youtube.track(url)
                except Exception as e:
                    print(e)
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_11"].format(
                    details["title"],
                    details["duration_min"],
                )
        elif await Platform.spotify.valid(url):
            spotify = True
            if not config.SPOTIFY_CLIENT_ID and not config.SPOTIFY_CLIENT_SECRET:
                return await mystic.edit_text(
                    "This Bot can't play spotify tracks and playlist, please contact my owner and ask him to add Spotify player."
                )
            if "track" in url:
                try:
                    details, track_id = await Platform.spotify.track(url)
                except Exception:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_11"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                try:
                    details, plist_id = await Platform.spotify.playlist(url)
                except Exception:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spplay"
                img = config.SPOTIFY_PLAYLIST_IMG_URL
                cap = _["play_12"].format(message.from_user.first_name)
            elif "album" in url:
                try:
                    details, plist_id = await Platform.spotify.album(url)
                except Exception:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spalbum"
                img = config.SPOTIFY_ALBUM_IMG_URL
                cap = _["play_12"].format(message.from_user.first_name)
            elif "artist" in url:
                try:
                    details, plist_id = await Platform.spotify.artist(url)
                except Exception:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "spartist"
                img = config.SPOTIFY_ARTIST_IMG_URL
                cap = _["play_12"].format(message.from_user.first_name)
            else:
                return await mystic.edit_text(_["play_17"])
        elif await Platform.apple.valid(url):
            if "album" in url:
                try:
                    details, track_id = await Platform.apple.track(url)
                except Exception:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "youtube"
                img = details["thumb"]
                cap = _["play_11"].format(details["title"], details["duration_min"])
            elif "playlist" in url:
                spotify = True
                try:
                    details, plist_id = await Platform.apple.playlist(url)
                except Exception:
                    return await mystic.edit_text(_["play_3"])
                streamtype = "playlist"
                plist_type = "apple"
                cap = _["play_13"].format(message.from_user.first_name)
                img = url
            else:
                return await mystic.edit_text(_["play_16"])
        elif await Platform.resso.valid(url):
            try:
                details, track_id = await Platform.resso.track(url)
            except Exception:
                return await mystic.edit_text(_["play_3"])
            streamtype = "youtube"
            img = details["thumb"]
            cap = _["play_11"].format(details["title"], details["duration_min"])
        elif await Platform.saavn.valid(url):
            if "shows" in url:
                return await mystic.edit_text(_["saavn_1"])

            elif await Platform.saavn.is_song(url):
                try:
                    file_path, details = await Platform.saavn.download(url)
                except Exception as e:
                    ex_type = type(e).__name__
                    LOGGER(__name__).error("An error occurred", exc_info=True)
                    return await mystic.edit_text(_["play_3"])
                duration_sec = details["duration_sec"]
                streamtype = "saavn_track"

                if duration_sec > config.DURATION_LIMIT:
                    return await mystic.edit_text(
                        _["play_6"].format(
                            config.DURATION_LIMIT_MIN,
                            details["duration_min"],
                        )
                    )
            elif await Platform.saavn.is_playlist(url):
                try:
                    details = await Platform.saavn.playlist(
                        url, limit=config.PLAYLIST_FETCH_LIMIT
                    )
                    streamtype = "saavn_playlist"
                except Exception as e:
                    ex_type = type(e).__name__
                    LOGGER(__name__).error("An error occurred", exc_info=True)
                    return await mystic.edit_text(_["play_3"])

                if len(details) == 0:
                    return await mystic.edit_text(_["play_3"])
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype=streamtype,
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    err = _["general_3"].format(ex_type)
                    LOGGER(__name__).error("An error occurred", exc_info=True)
                return await mystic.edit_text(err)
            return await mystic.delete()

        elif await Platform.soundcloud.valid(url):
            try:
                details, track_path = await Platform.soundcloud.download(url)
            except Exception:
                return await mystic.edit_text(_["play_3"])
            duration_sec = details["duration_sec"]
            if duration_sec > config.DURATION_LIMIT:
                return await mystic.edit_text(
                    _["play_6"].format(
                        config.DURATION_LIMIT_MIN,
                        details["duration_min"],
                    )
                )
            try:
                await stream(
                    _,
                    mystic,
                    user_id,
                    details,
                    chat_id,
                    user_name,
                    message.chat.id,
                    streamtype="soundcloud",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    LOGGER(__name__).error("An error occurred", exc_info=True)
                    err = _["general_3"].format(ex_type)
                return await mystic.edit_text(err)
            return await mystic.delete()
        else:
            if not await Platform.telegram.is_streamable_url(url):
                return await mystic.edit_text(_["play_19"])

            await mystic.edit_text(_["str_2"])
            try:
                await stream(
                    _,
                    mystic,
                    message.from_user.id,
                    url,
                    chat_id,
                    message.from_user.first_name,
                    message.chat.id,
                    video=video,
                    streamtype="index",
                    forceplay=fplay,
                )
            except Exception as e:
                ex_type = type(e).__name__
                if ex_type == "AssistantErr":
                    err = e
                else:
                    LOGGER(__name__).error("An error occurred", exc_info=True)
                    err = _["general_3"].format(ex_type)
                return await mystic.edit_text(err)
            return await play_logs(message, streamtype="M3u8 or Index Link")
    else:
        if len(message.command) < 2:
            buttons = botplaylist_markup(_)
            return await mystic.edit_text(
                _["playlist_1"],
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        slider = True
        query = message.text.split(None, 1)[1]
        if "-v" in query:
            query = query.replace("-v", "")
        try:
            details, track_id = await Platform.youtube.track(query)
        except Exception:
            return await mystic.edit_text(_["play_3"])
        streamtype = "youtube"
    if str(playmode) == "Direct" and not plist_type:
        if details["duration_min"]:
            duration_sec = time_to_seconds(details["duration_min"])
            if duration_sec > config.DURATION_LIMIT:
                return await mystic.edit_text(
                    _["play_6"].format(
                        config.DURATION_LIMIT_MIN,
                        details["duration_min"],
                    )
                )
        else:
            buttons = livestream_markup(
                _,
                track_id,
                user_id,
                "v" if video else "a",
                "c" if channel else "g",
                "f" if fplay else "d",
            )
            return await mystic.edit_text(
                _["play_15"],
                reply_markup=InlineKeyboardMarkup(buttons),
            )
        try:
            await stream(
                _,
                mystic,
                user_id,
                details,
                chat_id,
                user_name,
                message.chat.id,
                video=video,
                streamtype=streamtype,
                spotify=spotify,
                forceplay=fplay,
            )
        except Exception as e:
            ex_type = type(e).__name__
            if ex_type == "AssistantErr":
                err = e
            else:
                LOGGER(__name__).error("An error occurred", exc_info=True)

                err = _["general_3"].format(ex_type)
            return await mystic.edit_text(err)
        await mystic.delete()
        return await play_logs(message, streamtype=streamtype)
    else:
        if plist_type:
            ran_hash = "".join(
                random.choices(string.ascii_uppercase + string.digits, k=10)
            )
            lyrical[ran_hash] = plist_id
            buttons = playlist_markup(
                _,
                ran_hash,
                message.from_user.id,
                plist_type,
                "c" if channel else "g",
                "f" if fplay else "d",
            )
            await mystic.delete()
            await message.reply_photo(
                photo=img,
                caption=cap,
                reply_markup=InlineKeyboardMarkup(buttons),
            )
            return await play_logs(message, streamtype=f"Playlist : {plist_type}")
        else:
            if slider:
                buttons = slider_markup(
                    _,
                    track_id,
                    message.from_user.id,
                    query,
                    0,
                    "c" if channel else "g",
                    "f" if fplay else "d",
                )
                await mystic.delete()
                await message.reply_photo(
                    photo=details["thumb"],
                    caption=_["play_11"].format(
                        details["title"].title(),
                        details["duration_min"],
                    ),
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                return await play_logs(message, streamtype=f"Searched on Youtube")
            else:
                buttons = track_markup(
                    _,
                    track_id,
                    message.from_user.id,
                    "c" if channel else "g",
                    "f" if fplay else "d",
                )
                await mystic.delete()
                await message.reply_photo(
                    photo=img,
                    caption=cap,
                    reply_markup=InlineKeyboardMarkup(buttons),
                )
                return await play_logs(message, streamtype=f"URL Searched Inline")


__MODULE__ = "ᴘʟᴀʏ"
__HELP__ = """
<b>★ ᴘʟᴀʏ , ᴠᴘʟᴀʏ , ᴄᴘʟᴀʏ</b> - Aᴠᴀɪʟᴀʙʟᴇ Cᴏᴍᴍᴀɴᴅs
<b>★ ᴘʟᴀʏғᴏʀᴄᴇ , ᴠᴘʟᴀʏғᴏʀᴄᴇ , ᴄᴘʟᴀʏғᴏʀᴄᴇ</b> - FᴏʀᴄᴇPʟᴀʏ Cᴏᴍᴍᴀɴᴅs

<b>✦ c sᴛᴀɴᴅs ғᴏʀ ᴄʜᴀɴɴᴇʟ ᴘʟᴀʏ.</b>
<b>✦ v sᴛᴀɴᴅs ғᴏʀ ᴠɪᴅᴇᴏ ᴘʟᴀʏ.</b>
<b>✦ force sᴛᴀɴᴅs ғᴏʀ ғᴏʀᴄᴇ ᴘʟᴀʏ.</b>

<b>✧ /play ᴏʀ /vplay ᴏʀ /cplay</b> - Bᴏᴛ ᴡɪʟʟ sᴛᴀʀᴛ ᴘʟᴀʏɪɴɢ ʏᴏᴜʀ ɢɪᴠᴇɴ ǫᴜᴇʀʏ ᴏɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴏʀ Sᴛʀᴇᴀᴍ ʟɪᴠᴇ ʟɪɴᴋs ᴏɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛs.

<b>✧ /playforce ᴏʀ /vplayforce ᴏʀ /cplayforce</b> - Fᴏʀᴄᴇ Pʟᴀʏ sᴛᴏᴘs ᴛʜᴇ ᴄᴜʀʀᴇɴᴛ ᴘʟᴀʏɪɴɢ ᴛʀᴀᴄᴋ ᴏɴ ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ᴀɴᴅ sᴛᴀʀᴛs ᴘʟᴀʏɪɴɢ ᴛʜᴇ sᴇᴀʀᴄʜᴇᴅ ᴛʀᴀᴄᴋ ɪɴsᴛᴀɴᴛʟʏ ᴡɪᴛʜᴏᴜᴛ ᴅɪsᴛᴜʀʙɪɴɢ/ᴄʟᴇᴀʀɪɴɢ ǫᴜᴇᴜᴇ.

<b>✧ /channelplay [Cʜᴀᴛ ᴜsᴇʀɴᴀᴍᴇ ᴏʀ ɪᴅ] ᴏʀ [Dɪsᴀʙʟᴇ]</b> - Cᴏɴɴᴇᴄᴛ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴀ ɢʀᴏᴜᴘ ᴀɴᴅ sᴛʀᴇᴀᴍ ᴍᴜsɪᴄ ᴏɴ ᴄʜᴀɴɴᴇʟ's ᴠᴏɪᴄᴇ ᴄʜᴀᴛ ғʀᴏᴍ ʏᴏᴜʀ ɢʀᴏᴜᴘ.
"""
