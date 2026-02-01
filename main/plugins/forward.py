#Github.com/Vasusen-code

from .. import bot as Drone
from .. import userbot, Bot, AUTH
from main.plugins.helpers import get_link

from telethon import events, Button
from pyrogram.errors import FloodWait, ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid

@Drone.on(events.NewMessage(incoming=True, from_users=AUTH, pattern='/forward'))
async def forward_command(event):
    if not event.is_private:
        return
    
    async with Drone.conversation(event.chat_id) as conv:
        await conv.send_message("Send me the message link from group topic/forum that you want to forward, as a reply to this message.", buttons=Button.force_reply())
        try:
            link_msg = await conv.get_reply()
            try:
                msg_link = get_link(link_msg.text)
                if not msg_link:
                    await conv.send_message("No valid link found.")
                    return conv.cancel()
            except Exception:
                await conv.send_message("No link found.")
                return conv.cancel()
        except Exception as e:
            print(e)
            await conv.send_message("Cannot wait more longer for your response!")
            return conv.cancel()
        
        await conv.send_message("Send me the channel username or ID where you want to forward the message, as a reply to this message.", buttons=Button.force_reply())
        try:
            channel_msg = await conv.get_reply()
            channel = channel_msg.text.strip()
            # Remove @ if present
            if channel.startswith('@'):
                channel = channel[1:]
            # Try to parse as integer if it's a channel ID
            try:
                channel = int(channel)
            except ValueError:
                pass  # Keep as string if not a number
        except Exception as e:
            print(e)
            await conv.send_message("Cannot wait more longer for your response!")
            return conv.cancel()
        
        conv.cancel()
    
    # Parse message link to get chat and message ID
    edit = await event.reply("Processing...")
    
    try:
        # Handle different link formats
        # Format: t.me/c/chat_id/message_id or t.me/username/message_id
        # For forum topics: t.me/c/chat_id/topic_id/message_id
        if 't.me/c/' in msg_link:
            # Remove query parameters if any
            if '?' in msg_link:
                msg_link = msg_link.split('?')[0]
            parts = msg_link.split('/')
            # Find the index of 'c' in the URL
            c_index = parts.index('c')
            chat_id_str = parts[c_index + 1]
            
            # Check if it's a forum topic format (has 4 parts after 'c')
            if len(parts) > c_index + 3:
                # Forum topic format: t.me/c/chat_id/topic_id/message_id
                try:
                    # Try to parse as forum topic
                    int(parts[c_index + 2])  # topic_id
                    msg_id = int(parts[c_index + 3])
                except (ValueError, IndexError):
                    # Regular channel format: t.me/c/chat_id/message_id
                    msg_id = int(parts[c_index + 2])
            else:
                # Regular channel format: t.me/c/chat_id/message_id
                msg_id = int(parts[c_index + 2])
            
            chat_id = int('-100' + str(chat_id_str))
        elif 't.me/b/' in msg_link:
            # Bot message format: t.me/b/bot_username/message_id
            if '?' in msg_link:
                msg_link = msg_link.split('?')[0]
            parts = msg_link.split('/')
            b_index = parts.index('b')
            chat_id = str(parts[b_index + 1])
            msg_id = int(parts[b_index + 2])
        else:
            # Public channel format: t.me/username/message_id
            if '?' in msg_link:
                msg_link = msg_link.split('?')[0]
            parts = msg_link.split('/')
            # Find the username (after t.me/)
            chat_id = parts[3]  # username
            msg_id = int(parts[4])
        
        await edit.edit("Fetching message...")
        
        # Get the message using userbot
        try:
            msg = await userbot.get_messages(chat_id, msg_id)
            
            if not msg or msg.empty:
                await edit.edit("Message not found. Make sure the link is correct and you have access to the message.")
                return
            
            await edit.edit("Forwarding message...")
            
            # Forward the message to the channel
            await userbot.forward_messages(channel, chat_id, msg_id)
            
            await edit.edit(f"✅ Successfully forwarded message to {channel}!")
            
        except (ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid):
            await edit.edit("❌ Cannot access the source chat. Make sure you have joined the group/channel.")
        except PeerIdInvalid:
            await edit.edit("❌ Invalid channel destination. Please check the channel username or ID.")
        except FloodWait as fw:
            await edit.edit(f"❌ FloodWait: Try again after {fw.x} seconds.")
        except Exception as e:
            print(e)
            await edit.edit(f"❌ Error forwarding message: {str(e)}")
            
    except Exception as e:
        print(e)
        await edit.edit(f"❌ Error processing link: {str(e)}")
