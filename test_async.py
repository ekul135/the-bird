"""Test the async API"""
import asyncio
import aiohttp
import sys
sys.path.insert(0, 'custom_components/globird_energy')

from api import GlobirdergyClient, GlobirdergyAuthError

async def test():
    client = GlobirdergyClient()
    try:
        print("Testing login...")
        await client.login("your-email@example.com", "your-password")
        print("Login successful!")
        
        print("\nFetching accounts...")
        accounts = await client.get_accounts()
        print(f"Accounts: {accounts}")
        
    except GlobirdergyAuthError as e:
        print(f"Auth error: {e}")
    except aiohttp.ClientError as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
    finally:
        await client.close()

asyncio.run(test())
