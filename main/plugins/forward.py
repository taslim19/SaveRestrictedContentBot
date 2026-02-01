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
        thread_root_id = None  # The root message ID of the thread (could be topic header or first message in thread)
        
        try:
            # Get the reference message
            reference_msg = await userbot.get_messages(chat_id, reference_msg_id)
            print(f"Reference message ID: {reference_msg_id}")
            print(f"Message attributes: reply_to_top_id={getattr(reference_msg, 'reply_to_top_id', None)}, reply_to_message={getattr(reference_msg, 'reply_to_message', None)}")
            
            # Try multiple methods to find the topic header or thread root
            # Method 1: Check reply_to_top_id (most reliable)
            if hasattr(reference_msg, 'reply_to_top_id') and reference_msg.reply_to_top_id:
                topic_header_id = reference_msg.reply_to_top_id
                thread_root_id = topic_header_id
                print(f"Found topic header via reply_to_top_id: {topic_header_id}")
            # Method 2: Check if it replies to a message - that message might be in the topic thread
            elif hasattr(reference_msg, 'reply_to_message') and reference_msg.reply_to_message:
                reply_to = reference_msg.reply_to_message
                thread_root_id = reply_to.id  # This is the message being replied to
                print(f"Reference message replies to message ID: {thread_root_id}")
                
                # Check if the replied-to message is a topic header
                if hasattr(reply_to, 'forum_topic_created'):
                    topic_header_id = reply_to.id
                    print(f"Found topic header via reply_to_message (forum_topic_created): {topic_header_id}")
                # Check if the replied-to message has reply_to_top_id
                elif hasattr(reply_to, 'reply_to_top_id') and reply_to.reply_to_top_id:
                    topic_header_id = reply_to.reply_to_top_id
                    print(f"Found topic header via nested reply_to_top_id: {topic_header_id}")
                else:
                    # The replied-to message might be in the topic thread
                    # Try to find the topic header by checking if the replied-to message replies to something
                    try:
                        replied_to_msg = await userbot.get_messages(chat_id, reply_to.id)
                        if hasattr(replied_to_msg, 'reply_to_top_id') and replied_to_msg.reply_to_top_id:
                            topic_header_id = replied_to_msg.reply_to_top_id
                            print(f"Found topic header by checking replied-to message: {topic_header_id}")
                        elif hasattr(replied_to_msg, 'reply_to_message') and replied_to_msg.reply_to_message:
                            if hasattr(replied_to_msg.reply_to_message, 'forum_topic_created'):
                                topic_header_id = replied_to_msg.reply_to_message.id
                                print(f"Found topic header by checking nested reply: {topic_header_id}")
                    except Exception as e:
                        print(f"Could not check replied-to message: {e}")
            
            # Method 3: If reference message itself is a topic header
            if not topic_header_id and hasattr(reference_msg, 'forum_topic_created'):
                topic_header_id = reference_msg_id
                thread_root_id = topic_header_id
                print(f"Reference message is the topic header: {topic_header_id}")
            
            # Method 4: Try to find topic header by scanning recent messages
            if not topic_header_id:
                print("Topic header not found via reference message, scanning for topic header...")
                scan_count = 0
                # Look for messages with forum_topic_created near the reference message
                async for msg in userbot.get_chat_history(chat_id, limit=500):
                    scan_count += 1
                    if hasattr(msg, 'forum_topic_created'):
                        # Found a topic header - check if it's before our reference message
                        if msg.id <= reference_msg_id and msg.id <= thread_root_id if thread_root_id else reference_msg_id:
                            topic_header_id = msg.id
                            thread_root_id = msg.id
                            print(f"Found topic header by scanning: {msg.id}")
                            break
                    if scan_count >= 500:
                        break
            
            # If we still don't have topic_header_id but have thread_root_id, use that as starting point
            if not topic_header_id and thread_root_id:
                # Try to find the actual topic header by going up the reply chain
                current_id = thread_root_id
                for _ in range(10):  # Max 10 levels up
                    try:
                        msg = await userbot.get_messages(chat_id, current_id)
                        if hasattr(msg, 'forum_topic_created'):
                            topic_header_id = msg.id
                            print(f"Found topic header by traversing reply chain: {topic_header_id}")
                            break
                        elif hasattr(msg, 'reply_to_message') and msg.reply_to_message:
                            current_id = msg.reply_to_message.id
                        elif hasattr(msg, 'reply_to_top_id') and msg.reply_to_top_id:
                            topic_header_id = msg.reply_to_top_id
                            print(f"Found topic header via reply_to_top_id in chain: {topic_header_id}")
                            break
                        else:
                            break
                    except Exception:
                        break
                        
        except Exception as e:
            print(f"Error getting reference message: {e}")
            import traceback
            traceback.print_exc()
            await edit.edit(f"❌ Could not access the reference message. Error: {str(e)}")
            return
        
        if not topic_header_id and not thread_root_id:
            await edit.edit(f"❌ Could not identify topic header or thread root for topic {topic_id}. The message link might be invalid.")
            return
        
        # Use thread_root_id as fallback if topic_header_id not found
        search_root_id = topic_header_id if topic_header_id else thread_root_id
        print(f"Using search root ID: {search_root_id} (topic_header_id: {topic_header_id}, thread_root_id: {thread_root_id})")
        
        # Get all messages from the forum topic
        messages = []
        message_count = 0
        found_message_ids = set()  # Track found messages to avoid duplicates
        thread_message_ids = set()  # Track all message IDs in the thread
        
        if search_root_id:
            thread_message_ids.add(search_root_id)
        
        await edit.edit(f"Scanning messages in topic {topic_id} (root: {search_root_id})...")
        
        async for message in userbot.get_chat_history(chat_id, limit=None):
            message_count += 1
            belongs_to_topic = False
            
            # Method 1: Check reply_to_top_id (if available and we have topic_header_id)
            if topic_header_id and hasattr(message, 'reply_to_top_id') and message.reply_to_top_id:
                if message.reply_to_top_id == topic_header_id:
                    belongs_to_topic = True
                    thread_message_ids.add(message.id)
                    print(f"Message {message.id} in topic (reply_to_top_id matches {topic_header_id})")
            
            # Method 2: Check if message replies to thread root or any message in thread
            if not belongs_to_topic and search_root_id and hasattr(message, 'reply_to_message') and message.reply_to_message:
                reply_to_id = getattr(message.reply_to_message, 'id', None)
                if reply_to_id == search_root_id:
                    belongs_to_topic = True
                    thread_message_ids.add(message.id)
                    thread_message_ids.add(reply_to_id)
                    print(f"Message {message.id} in topic (replies to root {search_root_id})")
                # Check if it replies to a message that's already in our thread
                elif reply_to_id and reply_to_id in thread_message_ids:
                    belongs_to_topic = True
                    thread_message_ids.add(message.id)
                    print(f"Message {message.id} in topic (replies to thread message {reply_to_id})")
                # Check nested replies (message replies to something that replies to root)
                elif hasattr(message.reply_to_message, 'reply_to_message') and message.reply_to_message.reply_to_message:
                    nested_reply_id = getattr(message.reply_to_message.reply_to_message, 'id', None)
                    if nested_reply_id == search_root_id or (nested_reply_id and nested_reply_id in thread_message_ids):
                        belongs_to_topic = True
                        thread_message_ids.add(message.id)
                        thread_message_ids.add(reply_to_id)
                        print(f"Message {message.id} in topic (nested reply to {nested_reply_id})")
            
            # Method 3: Check forum_topic attribute in reply_to_message
            if not belongs_to_topic and hasattr(message, 'reply_to_message') and message.reply_to_message:
                if hasattr(message.reply_to_message, 'forum_topic') and message.reply_to_message.forum_topic:
                    if hasattr(message.reply_to_message.forum_topic, 'id'):
                        if message.reply_to_message.forum_topic.id == topic_id:
                            belongs_to_topic = True
                            thread_message_ids.add(message.id)
                            print(f"Message {message.id} in topic (forum_topic.id: {message.reply_to_message.forum_topic.id})")
            
            # Method 4: Include topic header/thread root itself
            if not belongs_to_topic and search_root_id and message.id == search_root_id:
                belongs_to_topic = True
                thread_message_ids.add(message.id)
                print(f"Message {message.id} is thread root/topic header")
            
            # Method 5: If message is the one being replied to by reference message
            if not belongs_to_topic and thread_root_id and message.id == thread_root_id:
                belongs_to_topic = True
                thread_message_ids.add(message.id)
                print(f"Message {message.id} is the message replied to by reference")
            
            if belongs_to_topic and message.id not in found_message_ids:
                messages.append(message)
                found_message_ids.add(message.id)
            
            # Update progress
            if message_count % 100 == 0:
                await edit.edit(f"Scanning messages... Found {len(messages)} messages in topic {topic_id} so far... (scanned {message_count} messages, thread has {len(thread_message_ids)} message IDs)")
            
            # Stop if we've scanned enough
            if message_count > 50000:
                print(f"Stopped scanning after {message_count} messages")
                break
        
        # Second pass: Find messages that reply to any message in the thread
        if thread_message_ids and len(messages) > 0:
            await edit.edit(f"Found {len(messages)} messages. Doing second pass to find all thread messages...")
            second_pass_count = 0
            async for message in userbot.get_chat_history(chat_id, limit=None):
                second_pass_count += 1
                if message.id in found_message_ids:
                    continue
                
                if hasattr(message, 'reply_to_message') and message.reply_to_message:
                    reply_to_id = getattr(message.reply_to_message, 'id', None)
                    if reply_to_id and reply_to_id in thread_message_ids:
                        messages.append(message)
                        found_message_ids.add(message.id)
                        thread_message_ids.add(message.id)
                        print(f"Second pass: Found message {message.id} (replies to {reply_to_id})")
                
                if second_pass_count % 100 == 0:
                    await edit.edit(f"Second pass... Found {len(messages)} messages total...")
                
                if second_pass_count > 50000:
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
