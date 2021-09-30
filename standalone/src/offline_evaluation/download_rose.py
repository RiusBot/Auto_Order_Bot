import pickle
from telethon import TelegramClient, events

# Remember to use your own values from my.telegram.org!
api_id = 8230873
api_hash = 'a7166dd79cbb76b0f3845557d7ee37a0'
client = TelegramClient('anon', api_id, api_hash)


async def main():
    rose_channel = await client.get_entity('🌹 Rose Premium Signal 2021')
    message_records = []
    async for message in client.iter_messages(rose_channel, reverse=False):
        message_records.append((message.text, message.date))
    return message_records
    
with client:
    message_records = client.loop.run_until_complete(main())


    
with open("rose_signal_history.pkl", "wb") as f:
    pickle.dump(message_records, f)