#Github.com/Vasusen-code

from .. import bot as Drone
from .. import userbot, Bot, AUTH
from main.plugins.helpers import get_link

from telethon import events, Button
from pyrogram.errors import FloodWait, ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, ChatInvalid, PeerIdInvalid
from pyrogram.enums import MessageMediaType
import os, time, asyncio
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
                # Try to get the channel - this will populate Pyrogram's cache
                dest_chat = None
                try:
                    dest_chat = await userbot.get_chat(channel)
                except (ChannelInvalid, ValueError) as e:
                    # If channel ID format might be wrong, try alternative
                    if isinstance(channel, int) and channel > 0:
                        # Try with -100 prefix for supergroups/channels
                        alt_channel = int('-100' + str(channel))
                        try:
                            dest_chat = await userbot.get_chat(alt_channel)
                            channel = alt_channel  # Update channel variable
                        except Exception:
                            # Try to access channel via get_chat_history to populate cache
                            try:
                                async for msg in userbot.get_chat_history(channel, limit=1):
                                    pass  # Just to populate cache
                                dest_chat = await userbot.get_chat(channel)
                            except Exception:
                                # Last resort: try with username if it was a number
                                raise e  # Re-raise original error
                    else:
                        raise e
                
                if dest_chat:
                    # Store the resolved channel ID
                    default_channels[event.sender_id] = dest_chat.id
                    await conv.send_message(f"✅ Default destination channel set to: {dest_chat.title if hasattr(dest_chat, 'title') else channel}\n(ID: {dest_chat.id})")
                else:
                    raise Exception("Failed to resolve channel")
            except ChannelInvalid:
                # If channel ID is invalid, try alternative formats
                if isinstance(channel, int):
                    # Try with -100 prefix if it's a positive number
                    if channel > 0:
                        try:
                            alt_channel = int('-100' + str(channel))
                            dest_chat = await userbot.get_chat(alt_channel)
                            default_channels[event.sender_id] = dest_chat.id
                            await conv.send_message(f"✅ Default destination channel set to: {dest_chat.title if hasattr(dest_chat, 'title') else alt_channel}\n(ID: {dest_chat.id})")
                        except Exception:
                            await conv.send_message(f"❌ Cannot access channel {channel}. Try using the channel username (e.g., @channelname) instead of ID, or make sure the userbot has joined the channel.")
                            return conv.cancel()
                    else:
                        await conv.send_message(f"❌ Invalid channel ID: {channel}. Try using the channel username (e.g., @channelname) instead.")
                        return conv.cancel()
                else:
                    await conv.send_message(f"❌ Cannot access channel '{channel}'. Make sure:\n1. The channel username is correct (without @)\n2. The userbot has joined the channel\n3. Try using the full channel ID format: -1001234567890")
                    return conv.cancel()
            except (ChannelPrivate, ChannelBanned):
                await conv.send_message(f"❌ Cannot access channel. The channel is private/banned or the userbot hasn't joined it. Please make sure the userbot account has joined the channel.")
                return conv.cancel()
            except Exception as e:
                error_msg = str(e)
                if "CHANNEL_INVALID" in error_msg or "ChannelInvalid" in error_msg:
                    await conv.send_message(f"❌ Invalid channel. Try:\n1. Using channel username: @channelname (without @)\n2. Using full channel ID: -1001234567890\n3. Make sure userbot has joined the channel")
                else:
                    await conv.send_message(f"❌ Cannot access channel. Error: {error_msg}\nMake sure the userbot has joined the channel.")
                return conv.cancel()
        except Exception as e:
            print(e)
            await conv.send_message("⏱️ Error occurred. Please try again.")
            return conv.cancel()
        
        conv.cancel()

@Drone.on(events.NewMessage(incoming=True, from_users=AUTH, pattern='/forwardall'))
async def forward_all_command(event):
    """Forward all messages from a forum topic"""
    if not event.is_private:
        return
    
    # Check if user has a default channel set
    default_channel = default_channels.get(event.sender_id)
    
    async with Drone.conversation(event.chat_id) as conv:
        await conv.send_message("Send me the forum topic link (e.g., t.me/c/chat_id/topic_id/message_id) to forward ALL messages from that topic.", buttons=Button.force_reply())
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
            await conv.send_message("⏱️ No response received. The conversation will wait for your response.")
            return conv.cancel()
        
        # Ask for channel only if no default is set
        if default_channel is None:
            await conv.send_message("Send me the channel:\n• Username: @channelname\n• Channel ID: -1001234567890\n• Or just the numeric ID: 1234567890\n\nReply with the channel username or ID. (Or use /channel to set a default)", buttons=Button.force_reply())
            try:
                channel_msg = await conv.get_reply()
                channel_input = channel_msg.text.strip()
                
                if channel_input.startswith('@'):
                    channel = channel_input[1:]
                elif channel_input.lstrip('-').isdigit():
                    channel = int(channel_input)
                    print(f"Channel ID provided: {channel}")
                else:
                    channel = channel_input
                    print(f"Channel username provided: {channel}")
            except asyncio.TimeoutError:
                await conv.send_message("⏱️ No response received. The conversation will wait for your response.")
                return conv.cancel()
            except Exception as e:
                print(e)
                await conv.send_message("⏱️ Error occurred. Please try again.")
                return conv.cancel()
        else:
            channel = default_channel
            await conv.send_message(f"Using default destination channel (ID: {default_channel}).\nSend a different channel to override, or send 'ok' to continue...", buttons=Button.force_reply())
            try:
                reply = await conv.get_reply()
                if reply and reply.text.strip().lower() not in ['ok', 'skip', 'continue', '']:
                    channel_input = reply.text.strip()
                    if channel_input.startswith('@'):
                        channel = channel_input[1:]
                    elif channel_input.lstrip('-').isdigit():
                        channel = int(channel_input)
                    else:
                        channel = channel_input
            except Exception:
                # No reply or error - use default channel
                pass
        
        conv.cancel()
    
    # Process the forward all command
    edit = await event.reply("Processing...")
    
    try:
        # Parse the forum topic link
        if 't.me/c/' not in msg_link:
            await edit.edit("❌ This command only works with forum topic links (t.me/c/chat_id/topic_id/message_id)")
            return
        
        if '?' in msg_link:
            msg_link = msg_link.split('?')[0]
        parts = msg_link.split('/')
        c_index = parts.index('c')
        
        if len(parts) <= c_index + 3:
            await edit.edit("❌ This doesn't appear to be a forum topic link. Use /forward for single messages.")
            return
        
        chat_id_str = parts[c_index + 1]
        topic_id = int(parts[c_index + 2])
        chat_id = int('-100' + str(chat_id_str))
        
        await edit.edit(f"Fetching all messages from topic {topic_id}...")
        
        # Get a reference message from the topic
        reference_msg_id = int(parts[c_index + 3])  # Message ID from the link
        topic_header_id = None
        reference_msg = None
        
        try:
            # Get the reference message
            reference_msg = await userbot.get_messages(chat_id, reference_msg_id)
            print(f"Reference message ID: {reference_msg_id}")
            print(f"Message attributes: reply_to_top_id={getattr(reference_msg, 'reply_to_top_id', None)}, reply_to_message={getattr(reference_msg, 'reply_to_message', None)}")
            
            # Try multiple methods to find the topic header
            # Method 1: Check reply_to_top_id
            if hasattr(reference_msg, 'reply_to_top_id') and reference_msg.reply_to_top_id:
                topic_header_id = reference_msg.reply_to_top_id
                print(f"Found topic header via reply_to_top_id: {topic_header_id}")
            # Method 2: Check if it replies to a message with forum_topic_created
            elif hasattr(reference_msg, 'reply_to_message') and reference_msg.reply_to_message:
                reply_to = reference_msg.reply_to_message
                if hasattr(reply_to, 'forum_topic_created'):
                    topic_header_id = reply_to.id
                    print(f"Found topic header via reply_to_message (forum_topic_created): {topic_header_id}")
                # Check if reply_to_message has a reply_to_top_id
                elif hasattr(reply_to, 'reply_to_top_id') and reply_to.reply_to_top_id:
                    topic_header_id = reply_to.reply_to_top_id
                    print(f"Found topic header via nested reply_to_top_id: {topic_header_id}")
                # Check if reply_to_message is the topic header itself
                elif hasattr(reply_to, 'forum_topic_created'):
                    topic_header_id = reply_to.id
                    print(f"Found topic header (reply_to is header): {topic_header_id}")
            
            # Method 3: If reference message itself is a topic header
            if not topic_header_id and hasattr(reference_msg, 'forum_topic_created'):
                topic_header_id = reference_msg_id
                print(f"Reference message is the topic header: {topic_header_id}")
            
            # Method 4: Try to find topic header by scanning recent messages
            if not topic_header_id:
                print("Topic header not found via reference message, scanning for topic header...")
                scan_count = 0
                async for msg in userbot.get_chat_history(chat_id, limit=1000):
                    scan_count += 1
                    if hasattr(msg, 'forum_topic_created'):
                        # Check if this topic matches our topic_id
                        # Topic IDs in forum are usually sequential, try to match
                        # Since we don't have direct topic_id in forum_topic_created,
                        # we'll use the message ID pattern or check nearby messages
                        if msg.id <= reference_msg_id:
                            topic_header_id = msg.id
                            print(f"Found potential topic header: {msg.id}")
                            break
                    if scan_count >= 1000:
                        break
                        
        except Exception as e:
            print(f"Error getting reference message: {e}")
            import traceback
            traceback.print_exc()
            await edit.edit(f"❌ Could not access the reference message. Error: {str(e)}")
            return
        
        if not topic_header_id:
            # Fallback: Use a different approach - scan messages and group by topic
            await edit.edit(f"⚠️ Could not find topic header. Trying alternative method to find topic {topic_id} messages...")
            topic_header_id = None  # We'll use topic_id directly
        
        # Get all messages from the forum topic
        messages = []
        message_count = 0
        
        await edit.edit(f"Scanning messages in topic {topic_id}...")
        
        async for message in userbot.get_chat_history(chat_id, limit=None):
            message_count += 1
            belongs_to_topic = False
            
            # Method 1: Check reply_to_top_id (if available)
            if topic_header_id and hasattr(message, 'reply_to_top_id') and message.reply_to_top_id:
                if message.reply_to_top_id == topic_header_id:
                    belongs_to_topic = True
                    print(f"Message {message.id} in topic (reply_to_top_id matches)")
            
            # Method 2: Check if message replies to topic header
            if not belongs_to_topic and topic_header_id and hasattr(message, 'reply_to_message') and message.reply_to_message:
                if hasattr(message.reply_to_message, 'id') and message.reply_to_message.id == topic_header_id:
                    belongs_to_topic = True
                    print(f"Message {message.id} in topic (replies to header {topic_header_id})")
                # Check nested replies
                elif hasattr(message.reply_to_message, 'reply_to_message') and message.reply_to_message.reply_to_message:
                    if hasattr(message.reply_to_message.reply_to_message, 'id') and message.reply_to_message.reply_to_message.id == topic_header_id:
                        belongs_to_topic = True
            
            # Method 3: Check forum_topic attribute in reply_to_message
            if not belongs_to_topic and hasattr(message, 'reply_to_message') and message.reply_to_message:
                if hasattr(message.reply_to_message, 'forum_topic') and message.reply_to_message.forum_topic:
                    if hasattr(message.reply_to_message.forum_topic, 'id'):
                        if message.reply_to_message.forum_topic.id == topic_id:
                            belongs_to_topic = True
                            print(f"Message {message.id} in topic (forum_topic.id: {message.reply_to_message.forum_topic.id})")
            
            # Method 4: Include topic header itself
            if not belongs_to_topic and topic_header_id and message.id == topic_header_id:
                belongs_to_topic = True
                print(f"Message {message.id} is topic header")
            
            # Method 5: If we have the reference message, check if messages are in the same thread
            # by checking if they have similar reply patterns
            if not belongs_to_topic and reference_msg:
                # Check if message and reference_msg share the same reply chain
                if hasattr(message, 'reply_to_message') and message.reply_to_message:
                    if hasattr(reference_msg, 'reply_to_message') and reference_msg.reply_to_message:
                        # If both reply to messages with similar IDs (same topic thread)
                        ref_reply_id = getattr(reference_msg.reply_to_message, 'id', None)
                        msg_reply_id = getattr(message.reply_to_message, 'id', None)
                        if ref_reply_id and msg_reply_id:
                            # Messages in same topic often reply to messages close to each other
                            if abs(ref_reply_id - msg_reply_id) < 100:
                                # Further check: see if they're in same reply chain
                                belongs_to_topic = True
                                print(f"Message {message.id} in topic (similar reply chain)")
            
            if belongs_to_topic:
                messages.append(message)
            
            # Update progress
            if message_count % 100 == 0:
                await edit.edit(f"Scanning messages... Found {len(messages)} messages in topic {topic_id} so far... (scanned {message_count} messages)")
            
            # Stop if we've scanned enough and found messages, or if we've gone too far
            if message_count > 50000:
                print(f"Stopped scanning after {message_count} messages")
                break
        
        messages.reverse()
        
        if not messages:
            await edit.edit(f"❌ No messages found in topic {topic_id}. Make sure the topic exists and you have access.")
            return
        
        await edit.edit(f"Found {len(messages)} messages in topic {topic_id}. Verifying destination channel...")
        
        # Verify destination channel
        dest_chat_id = channel
        try:
            dest_chat = await userbot.get_chat(channel)
            dest_chat_id = dest_chat.id
            if hasattr(dest_chat, 'type'):
                if dest_chat.type.name not in ['CHANNEL', 'SUPERGROUP', 'GROUP']:
                    await edit.edit(f"❌ Destination must be a channel or group, not a {dest_chat.type.name.lower()}.")
                    return
        except ChannelInvalid:
            # If channel ID is invalid, try alternative formats
            if isinstance(channel, int):
                if channel > 0:
                    try:
                        alt_channel = int('-100' + str(channel))
                        dest_chat = await userbot.get_chat(alt_channel)
                        dest_chat_id = dest_chat.id
                        print(f"Resolved channel using alternative format: {dest_chat_id}")
                    except Exception:
                        await edit.edit(f"❌ Invalid channel ID: {channel}. Try using the channel username (e.g., @channelname) instead, or make sure the userbot has joined the channel.")
                        return
                else:
                    await edit.edit(f"❌ Invalid channel ID: {channel}. Try using the channel username (e.g., @channelname) instead.")
                    return
            else:
                await edit.edit(f"❌ Cannot access channel '{channel}'. Make sure:\n1. The channel username is correct\n2. The userbot has joined the channel\n3. Try using the full channel ID: -1001234567890")
                return
        except (ChannelPrivate, ChannelBanned):
            await edit.edit(f"❌ Cannot access destination channel. The channel is private/banned or the userbot hasn't joined it. Please make sure the userbot account has joined the channel.")
            return
        except Exception as e:
            error_msg = str(e)
            if "CHANNEL_INVALID" in error_msg or "ChannelInvalid" in error_msg:
                await edit.edit(f"❌ Invalid channel. Try:\n1. Using channel username: @channelname (without @)\n2. Using full channel ID: -1001234567890\n3. Make sure userbot has joined the channel")
            else:
                await edit.edit(f"❌ Cannot access destination channel {channel}. Error: {error_msg}")
            return
        
        # Copy all messages
        await edit.edit(f"Copying {len(messages)} message(s) to channel (without forward attribution)...")
        copied_count = 0
        failed_count = 0
        
        for idx, msg in enumerate(messages, 1):
            try:
                if idx % 10 == 0 or idx == len(messages):
                    await edit.edit(f"Copying message {idx}/{len(messages)} to channel...")
                copied = await userbot.copy_message(dest_chat_id, chat_id, msg.id)
                copied_count += 1
                
                if idx < len(messages):
                    await asyncio.sleep(1)
            except FloodWait as fw:
                await edit.edit(f"⏳ FloodWait: Waiting {fw.x} seconds before continuing...")
                await asyncio.sleep(fw.x)
                try:
                    copied = await userbot.copy_message(dest_chat_id, chat_id, msg.id)
                    copied_count += 1
                except Exception as e:
                    print(f"Failed to copy message {msg.id}: {e}")
                    failed_count += 1
            except Exception as e:
                print(f"Failed to copy message {msg.id}: {e}")
                failed_count += 1
        
        success_msg = f"✅ Successfully copied {copied_count} message(s) from topic {topic_id} to {channel}!"
        if failed_count > 0:
            success_msg += f"\n⚠️ {failed_count} message(s) failed to copy."
        
        await edit.edit(success_msg)
        
    except Exception as e:
        print(f"Forward all error: {e}")
        await edit.edit(f"❌ Error: {str(e)}")

@Drone.on(events.NewMessage(incoming=True, from_users=AUTH, pattern='/forward'))
async def forward_command(event):
    """Forward a single message"""
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
            await conv.send_message("⏱️ No response received. The conversation will wait for your response.")
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
            except asyncio.TimeoutError:
                await conv.send_message("⏱️ No response received. The conversation will wait for your response.")
                return conv.cancel()
            except Exception as e:
                print(e)
                await conv.send_message("⏱️ Error occurred. Please try again.")
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
        # For forum topics: t.me/c/chat_id/topic_id/message_id (but we only forward the single message)
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
                # For /forward, we only forward the single specified message
                try:
                    int(parts[c_index + 2])  # topic_id (we don't need it for single message)
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
        
        # Get the single message using userbot
        try:
            msg = await userbot.get_messages(chat_id, msg_id)
            
            if not msg or msg.empty:
                await edit.edit("Message not found. Make sure the link is correct and you have access to the message.")
                return
            
            messages = [msg]  # Single message
            
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
            except ChannelInvalid:
                # If channel ID is invalid, try alternative formats
                if isinstance(channel, int):
                    if channel > 0:
                        try:
                            alt_channel = int('-100' + str(channel))
                            dest_chat = await userbot.get_chat(alt_channel)
                            dest_chat_id = dest_chat.id
                            print(f"Resolved channel using alternative format: {dest_chat_id}")
                        except Exception:
                            await edit.edit(f"❌ Invalid channel ID: {channel}. Try using the channel username (e.g., @channelname) instead, or make sure the userbot has joined the channel.")
                            return
                    else:
                        await edit.edit(f"❌ Invalid channel ID: {channel}. Try using the channel username (e.g., @channelname) instead.")
                        return
                else:
                    await edit.edit(f"❌ Cannot access channel '{channel}'. Make sure:\n1. The channel username is correct\n2. The userbot has joined the channel\n3. Try using the full channel ID: -1001234567890")
                    return
            except (ChannelPrivate, ChannelBanned):
                await edit.edit(f"❌ Cannot access destination channel. The channel is private/banned or the userbot hasn't joined it. Please make sure the userbot account has joined the channel.")
                return
            except ValueError as ve:
                if "Peer id invalid" in str(ve):
                    await edit.edit(f"❌ Cannot access destination channel {channel}. Make sure the userbot has joined the channel and has permission to send messages.")
                    return
                else:
                    raise
            except Exception as e:
                error_msg = str(e)
                print(f"Error accessing destination channel: {e}")
                if "CHANNEL_INVALID" in error_msg or "ChannelInvalid" in error_msg:
                    await edit.edit(f"❌ Invalid channel. Try:\n1. Using channel username: @channelname (without @)\n2. Using full channel ID: -1001234567890\n3. Make sure userbot has joined the channel")
                else:
                    await edit.edit(f"❌ Cannot access destination channel {channel}. Error: {error_msg}")
                return
            
            await edit.edit("Copying message to channel (without forward attribution)...")
            
            # Copy the single message instead of forwarding to hide sender name
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
