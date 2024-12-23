import discord
from discord.ext import commands
from gradio_client import Client, handle_file
import logging
import config  # Ensure this contains sensitive data like BOT_TOKEN and HUGGINGFACE_SPACE_NAME

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/bot.log"),  # Log to a file
        logging.StreamHandler()  # Log to the terminal
    ],
)

# Application ID
APPLICATION_ID = config.APPLICATION_ID

# Setup Discord Intents
intents = discord.Intents.default()
intents.message_content = True  # Required to read messages
bot = commands.Bot(command_prefix="?", intents=intents)

# Hugging Face API Details
HUGGINGFACE_SPACE_NAME = config.HUGGINGFACE_SPACE_NAME
client = Client(HUGGINGFACE_SPACE_NAME)

# Track users who have received the initial instructions
seen_users = set()

@bot.event
async def on_message(message):
    # Ignore bot's own messages to avoid loops
    if message.author == bot.user:
        return

    # Check if the message is a DM to the bot
    if isinstance(message.channel, discord.DMChannel):
        if message.author.id not in seen_users:
            # Send the available commands list only once
            embed = discord.Embed(
                title="Welcome to the Bot!",
                description=(
                    "Hi! 👋 Here are the commands you can use:\n\n"
                    "🔹 **?upload** - Process an image and overlay text.\n"
                    "   Example: `?upload \"Your text here\"` (attach an image).\n\n"
                    "🔹 **?instructions** - View the instructions again.\n\n"
                    "Feel free to ask me for help anytime! 🎨"
                ),
                color=discord.Color.blue()
            )
            await message.channel.send(embed=embed)
            seen_users.add(message.author.id)  # Mark the user as seen

    # Process commands normally
    await bot.process_commands(message)

@bot.event
async def on_ready():
    logging.info(f"Bot is online as {bot.user}")
    print(f"Bot is online as {bot.user}")
    print(f"Invite the bot using: https://discord.com/oauth2/authorize?client_id={APPLICATION_ID}&permissions=1099511680048&scope=bot")

@bot.command()
async def instructions(ctx):
    """Send the 'how to use' instructions when requested."""
    embed = discord.Embed(
        title="How to Use the Bot",
        description=(
            "Hi! 👋 Here are the commands you can use:\n\n"
            "🔹 **?upload** - Process an image and overlay text.\n"
            "   Example: `?upload \"Your text here\"` (attach an image).\n\n"
            "🔹 **?instructions** - View the instructions again.\n\n"
            "Feel free to ask me for help anytime! 🎨"
        ),
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

@bot.command()
async def upload(ctx, *, overlay_text: str = None):
    """Handles image uploads and overlays text using the Hugging Face API."""
    if not ctx.message.attachments:
        await ctx.send("Please attach an image to process.")
        return

    if not overlay_text:
        await ctx.send("Please provide text to overlay on the image. Example: `?upload Hello World!`")
        return

    try:
        # Get the uploaded image
        attachment = ctx.message.attachments[0]
        image_data = await attachment.read()

        # Save the image temporarily
        temp_image_path = f"temp_{attachment.filename}"
        with open(temp_image_path, "wb") as f:
            f.write(image_data)
        logging.info(f"Image saved temporarily to: {temp_image_path}")

        # Prepare the payload for the API
        logging.info(f"Overlay text: {overlay_text}")
        payload = {
            "image": handle_file(temp_image_path),
            "text": overlay_text.strip()  # Ensure clean text
        }
        logging.info(f"Payload being sent to API: {payload}")

        # Send the request to the Hugging Face API
        result = client.predict(
            image=payload["image"],
            text=payload["text"],
            api_name="/predict"
        )
        logging.info(f"API Response: {result}")

        # Send the processed image back to Discord
        if isinstance(result, tuple) and len(result) >= 2:
            processed_image_path = result[1]
            status_message = result[2] if len(result) > 2 else "Processing complete!"
            await ctx.send(status_message, file=discord.File(processed_image_path))
        else:
            await ctx.send(f"Unexpected response format: {result}")

    except Exception as e:
        logging.error(f"Error processing ?upload command: {e}")
        await ctx.send(f"An error occurred while processing the image: {e}")

try:
    bot.run(config.BOT_TOKEN)  # Token is imported securely from the configuration file
except Exception as e:
    logging.critical(f"Failed to start the bot: {e}")
    print(f"Failed to start the bot: {e}")
