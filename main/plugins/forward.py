#Github.com/Vasusen-code

from .. import bot as Drone
from .. import userbot, Bot, AUTH
from main.plugins.helpers import get_link

from telethon import events, Button
from pyrogram.errors import FloodWait, ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid
from pyrogram.enums import MessageMediaType
import os, time
from main.plugins.progress import progress_for_pyrogram
from main.plugins.helpers import screenshot
from ethon.pyfunc import video_metadata

# Store default destination channels per user (user_id -> channel_id/username)
default_channels = {}

@Drone.on(events.NewMessage(incoming=True, from_users=AUTH, pattern='/channel'))
async def set_channel_command(event):
    """Set default destination channel for forwarding"""
    if not event.is_private:
        return
    
    async with Drone.conversation(event.chat_id) as conv:
        await conv.send_message("Send me the channel:\n• Username: @channelname\n• Channel ID: -1001234567890\n• Or just the numeric ID: 1234567890\n\nThis will be set as your default destination channel.", buttons=Button.force_reply())
        try:
            channel_msg = await conv.get_reply()
            channel_input = channel_msg.text.strip()
            
            # Handle different channel ID formats
            if channel_input.startswith('@'):
                channel = channel_input[1:]  # Username without @
            elif channel_input.lstrip('-').isdigit():
                channel = int(channel_input)
            else:
                channel = channel_input
            
            # Verify the channel exists and is accessible
            try:
                dest_chat = await userbot.get_chat(channel)
                # Store the resolved channel ID
                default_channels[event.sender_id] = dest_chat.id
                await conv.send_message(f"✅ Default destination channel set to: {dest_chat.title if hasattr(dest_chat, 'title') else channel}\n(ID: {dest_chat.id})")
            except Exception as e:
                await conv.send_message(f"❌ Cannot access channel. Error: {str(e)}\nMake sure the userbot has joined the channel.")
                return conv.cancel()
        except Exception as e:
            print(e)
            await conv.send_message("Cannot wait more longer for your response!")
            return conv.cancel()
        
        conv.cancel()

@Drone.on(events.NewMessage(incoming=True, from_users=AUTH, pattern='/forward'))
async def forward_command(event):
    if not event.is_private:
        return
    
    # Check if user has a default channel set
    default_channel = default_channels.get(event.sender_id)
    
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
        
        # Ask for channel only if no default is set
        if default_channel is None:
            await conv.send_message("Send me the channel:\n• Username: @channelname\n• Channel ID: -1001234567890\n• Or just the numeric ID: 1234567890\n\nReply with the channel username or ID. (Or use /channel to set a default)", buttons=Button.force_reply())
            try:
                channel_msg = await conv.get_reply()
                channel_input = channel_msg.text.strip()
                
                # Handle different channel ID formats
                if channel_input.startswith('@'):
                    channel = channel_input[1:]  # Username without @
                elif channel_input.lstrip('-').isdigit():
                    channel = int(channel_input)
                    print(f"Channel ID provided: {channel}")
                else:
                    channel = channel_input
                    print(f"Channel username provided: {channel}")
            except Exception as e:
                print(e)
                await conv.send_message("Cannot wait more longer for your response!")
                return conv.cancel()
        else:
            # Use default channel
            channel = default_channel
            await conv.send_message(f"Using default destination channel (ID: {default_channel}).\nSend a different channel to override, or send 'ok' to continue...", buttons=Button.force_reply())
            try:
                # Wait for user to optionally override or confirm
                reply = await conv.get_reply()
                if reply and reply.text.strip().lower() not in ['ok', 'skip', 'continue', '']:
                    # User wants to override
                    channel_input = reply.text.strip()
                    if channel_input.startswith('@'):
                        channel = channel_input[1:]
                    elif channel_input.lstrip('-').isdigit():
                        channel = int(channel_input)
                    else:
                        channel = channel_input
            except Exception:
                # No reply or error - use default
                pass
        
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
            
            await edit.edit("Verifying destination channel...")
            
            # Verify and resolve the destination channel
            dest_chat_id = channel  # Default to original value
            try:
                # Try to get the channel to ensure userbot has access
                dest_chat = await userbot.get_chat(channel)
                print(f"Destination channel: {dest_chat.title if hasattr(dest_chat, 'title') else channel}")
                print(f"Destination chat ID: {dest_chat.id}, Type: {dest_chat.type if hasattr(dest_chat, 'type') else 'unknown'}")
                
                # Use the resolved chat ID for forwarding
                dest_chat_id = dest_chat.id
                
                # Ensure it's a channel/group, not a private chat
                if hasattr(dest_chat, 'type'):
                    if dest_chat.type.name not in ['CHANNEL', 'SUPERGROUP', 'GROUP']:
                        await edit.edit(f"❌ Destination must be a channel or group, not a {dest_chat.type.name.lower()}.")
                        return
            except ValueError as ve:
                if "Peer id invalid" in str(ve):
                    await edit.edit(f"❌ Cannot access destination channel {channel}. Make sure the userbot has joined the channel and has permission to send messages.")
                    return
                else:
                    raise
            except Exception as e:
                print(f"Error accessing destination channel: {e}")
                await edit.edit(f"❌ Cannot access destination channel {channel}. Error: {str(e)}")
                return
            
            await edit.edit("Copying message to channel (without forward attribution)...")
            
            # Copy the message instead of forwarding to hide sender name
            # copy_message sends the message as if it was sent by the bot, hiding forward info
            # Use the resolved channel ID
            print(f"Copying message {msg_id} from {chat_id} to {dest_chat_id}")
            
            copied = await userbot.copy_message(dest_chat_id, chat_id, msg_id)
            
            print(f"Copy successful. Message copied to {dest_chat_id}, message ID: {copied.id}")
            
            await edit.edit(f"✅ Successfully copied message to {channel} (without forward attribution)!")
            
        except (ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid) as e:
            if "source" in str(e).lower() or chat_id in str(e):
                await edit.edit("❌ Cannot access the source chat. Make sure you have joined the group/channel.")
            else:
                await edit.edit(f"❌ Cannot access destination channel. Error: {str(e)}")
        except PeerIdInvalid:
            await edit.edit("❌ Invalid channel destination. Please check the channel username or ID. Make sure the userbot has joined the destination channel.")
        except FloodWait as fw:
            await edit.edit(f"❌ FloodWait: Try again after {fw.x} seconds.")
        except ValueError as ve:
            if "Peer id invalid" in str(ve):
                await edit.edit(f"❌ Cannot resolve peer ID. Make sure:\n1. Userbot has joined the source group/channel\n2. Userbot has joined the destination channel\n3. Userbot has permission to forward messages")
            else:
                await edit.edit(f"❌ Error: {str(ve)}")
        except Exception as e:
            print(f"Forward error: {e}")
            error_msg = str(e)
            if "CHAT_ADMIN_REQUIRED" in error_msg or "admin" in error_msg.lower():
                await edit.edit("❌ Userbot needs admin rights in the destination channel to forward messages.")
            elif "not found" in error_msg.lower() or "doesn't exist" in error_msg.lower():
                await edit.edit("❌ Destination channel not found. Check the channel username or ID.")
            else:
                await edit.edit(f"❌ Error forwarding message: {error_msg}")
            
    except Exception as e:
        print(e)
        await edit.edit(f"❌ Error processing link: {str(e)}")
