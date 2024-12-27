import os
import asyncio
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from discord import Intents, Client
import aiohttp

load_dotenv()

TOKEN = os.getenv('TOKEN')
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

intents = Intents.default()
intents.message_content = True
client = Client(intents=intents)

last_word = None


async def get_word_and_definition():
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }

        async with aiohttp.ClientSession() as session:
            async with session.get('https://www.dictionary.com/e/word-of-the-day/', headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"HTTP Error: {response.status}")
                html = await response.text()

        soup = BeautifulSoup(html, 'html.parser')

        # Extract the word
        word_element = soup.find('div', class_='otd-item-headword__word')
        word = word_element.text.strip() if word_element else None

        # Extract part of speech
        pos_element = soup.find('div', class_='otd-item-headword__pos')
        part_of_speech = pos_element.find('span',
                                          class_='italic').text.strip() if pos_element else "Part of speech not found"

        # Extract pronunciation and phonetic respelling
        pronunciation_element = soup.find('span', class_='otd-item-headword__pronunciation__text')
        pronunciation = pronunciation_element.text.strip() if pronunciation_element else "Pronunciation not found"

        ipa_element = soup.find('span', class_='otd-item-headword__ipa')
        phonetic_respelling = ipa_element.text.strip() if ipa_element else None

        # Extract definition (specifically second <p> in `otd-item-headword__pos-blocks`)
        definition_block = soup.find('div', class_='otd-item-headword__pos-blocks')
        definition_element = definition_block.find_all('p')[1] if definition_block else None
        definition = definition_element.text.strip() if definition_element else "Definition not found"

        # Extract more about the word
        more_about_element = soup.find('div', class_='wotd-item-origin__content')
        more_about = None
        examples = []
        if more_about_element:
            # Combine all text content, clean extra lines
            raw_text = '\n'.join([line.strip() for line in more_about_element.stripped_strings])

            # Remove redundant "More about [word]"
            more_about_pattern = f"More about {word}"
            if more_about_pattern in raw_text:
                raw_text = raw_text.replace(more_about_pattern, "").strip()

            # Separate "EXAMPLES OF [WORD]" and split examples
            examples_pattern = f"EXAMPLES OF {word.upper()}"
            if examples_pattern in raw_text:
                more_about_text, examples_text = raw_text.split(examples_pattern, 1)
                more_about = ' '.join(more_about_text.split())  # Clean extra whitespace
                # Extract examples, clean whitespace, and join without extra newlines
                examples = [
                    ' '.join(example.strip().split())  # Remove redundant spaces
                    for example in examples_text.split('\n') 
                    if example.strip() and not example.strip().isspace()
                ]
            else:
                more_about = ' '.join(raw_text.split())  # Clean extra whitespace

        return word, part_of_speech, pronunciation, phonetic_respelling, definition, more_about, examples
    except Exception as e:
        print(f"Error fetching word: {e}")
        return None, None, None, None, None, None, None


async def check_and_send_word():
    global last_word
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print(f"Error: Could not find channel with ID {CHANNEL_ID}. Make sure the bot has access.")
        return

    while True:
        word, part_of_speech, pronunciation, phonetic_respelling, definition, more_about, examples = await get_word_and_definition()
        if word and word != last_word:
            last_word = word
            message = f"**Word of the Day:** {word}\n\n"
            message += f"**Part of Speech:** {part_of_speech}\n"
            message += f"**Pronunciation:** {pronunciation}\n"
            if phonetic_respelling:
                message += f"**Phonetic Respelling:** {phonetic_respelling}\n"
            message += f"**Definition:** {definition}\n\n"

            if more_about:
                message += f"**More About This Word:**\n{more_about}\n\n"

            if examples:
                message += "**Examples:**\n"
                for i, example in enumerate(examples, 1):
                    message += f"{i}. {example}\n"

            await channel.send(message)
        await asyncio.sleep(3600)  # Check every hour for a new word


@client.event
async def on_ready():
    print(f"Bot is ready and running as {client.user}")
    client.loop.create_task(check_and_send_word())


def main():
    client.run(TOKEN)


if __name__ == "__main__":
    main()
