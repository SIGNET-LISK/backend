import asyncio
import logging
import os
import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_URL = os.getenv("API_URL_BOT", "http://localhost:8000/api")

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 **SIGNET Bot Online.**\nSend a Video, Photo, or Link to verify authenticity.")

import io

# Helper function for verification
async def verify_content(file_name, file_data, mime_type, status_msg):
    try:
        files = {'file': (file_name, file_data, mime_type)}
        response = requests.post(f"{API_URL}/verify", files=files)
        
        if response.status_code == 200:
            result = response.json()
            status_icon = "✅" if result['status'] == "VERIFIED" else "⚠️"
            
            text = f"{status_icon} **{result['status']}**\n\n"
            text += f"📜 **Title:** {result.get('title', 'N/A')}\n"
            text += f"👤 **Publisher:** {result.get('publisher', 'N/A')}\n"
            text += f"📏 **Distance:** {result.get('hamming_distance', 'N/A')}\n"
            text += f"🔗 [Explorer Link]({result.get('explorer_link', '#')})\n"
            text += f"\n_{result.get('message', '')}_"
            
            await status_msg.edit_text(text, parse_mode="Markdown")
        else:
            await status_msg.edit_text(f"❌ Verification failed: {response.text}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

@dp.message(F.photo | F.video | F.document)
async def handle_media(message: types.Message):
    status_msg = await message.answer("⏳ Downloading and verifying...")
    
    file_id = None
    file_name = "unknown"
    mime_type = ""

    if message.photo:
        file_id = message.photo[-1].file_id
        file_name = "image.jpg"
        mime_type = "image/jpeg"
    elif message.video:
        file_id = message.video.file_id
        file_name = message.video.file_name or "video.mp4"
        mime_type = message.video.mime_type
    elif message.document:
        file_id = message.document.file_id
        file_name = message.document.file_name
        mime_type = message.document.mime_type

    if not file_id:
        await status_msg.edit_text("❌ Unsupported media type.")
        return

    try:
        file = await bot.get_file(file_id)
        file_path = file.file_path
        
        # Download file
        downloaded_file = await bot.download_file(file_path)
        
        # Verify
        await verify_content(file_name, downloaded_file, mime_type, status_msg)

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

import yt_dlp
import os

@dp.message(F.text)
async def handle_text(message: types.Message):
    if message.text.startswith("http"):
        status_msg = await message.answer("⏳ Analyzing link with yt-dlp...")
        url = message.text
        
        try:
            # Try yt-dlp first for social media links
            ydl_opts = {
                'format': 'best',
                'quiet': True,
                'outtmpl': 'temp_media.%(ext)s',
                'max_filesize': 50 * 1024 * 1024 # Limit 50MB
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                
                if not os.path.exists(filename):
                     await status_msg.edit_text("❌ Failed to download media from link.")
                     return
                     
                mime_type = "video/mp4" # Default guess
                if filename.endswith(".jpg") or filename.endswith(".png") or filename.endswith(".webp"):
                    mime_type = "image/jpeg"
                
                # Read file
                with open(filename, 'rb') as f:
                    file_data = f.read()
                
                # Clean up
                os.remove(filename)
                
                await status_msg.edit_text("⏳ Verifying extracted media...")
                await verify_content(filename, file_data, mime_type, status_msg)
                
        except Exception as e:
             # Fallback to direct download if yt-dlp fails (for direct links)
             try:
                response = requests.get(url, stream=True)
                content_type = response.headers.get('Content-Type', '')
                
                if 'image' in content_type or 'video' in content_type:
                    file_name = "url_content"
                    if 'image' in content_type: file_name += ".jpg"
                    elif 'video' in content_type: file_name += ".mp4"
                    
                    file_data = io.BytesIO(response.content)
                    await verify_content(file_name, file_data, content_type, status_msg)
                    return
             except:
                pass
                
             await status_msg.edit_text(f"❌ Failed to process link: {str(e)}")
    else:
        await message.answer("Please send a file or link.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
