import asyncio
from datetime import datetime, timezone
from web3 import AsyncWeb3, AsyncBaseProvider
from web3.providers import AsyncHTTPProvider
from src.utils.logger import get_logger
from src.db.database import AsyncSessionLocal
from src.db import models
from src.utils.redis_client import get_redis
import json

logger = get_logger(__name__)

# Public RPC endpoints (no API key required)
ARBITRUM_SEPOLIA_PUBLIC_RPCS = [
    "https://sepolia-rollup.arbitrum.io/rpc",
    "https://arbitrum-sepolia.public.blastapi.io",
    "https://endpoints.omniatech.io/v1/arbitrum/sepolia/public",
]

# WebSocket endpoints (for real-time listening)
ARBITRUM_SEPOLIA_WS = [
    "wss://arbitrum-sepolia.public.blastapi.io",
    "wss://endpoints.omniatech.io/v1/arbitrum/sepolia/public/ws",
]

async def listen_blocks():
    """Listen for new blocks on Arbitrum testnet using public endpoints."""
    # Try WebSocket endpoints first
    for ws_url in ARBITRUM_SEPOLIA_WS:
        try:
            logger.info(f"Attempting WebSocket connection to {ws_url}")
            provider = AsyncBaseProvider(ws_url)
            w3 = AsyncWeb3(provider)
            
            # Connect to the WebSocket provider
            await w3.provider.connect()
            logger.info(f"Connected to {ws_url}")
            
            # Create a filter for new blocks
            block_filter = await w3.eth.filter("latest")
            logger.info("Created block filter, listening for new blocks...")
            
            while True:
                try:
                    # Get new block entries
                    new_blocks = await block_filter.get_new_entries()
                    for block_hash in new_blocks:
                        # Get full block data
                        block_data = await w3.eth.get_block(block_hash)
                        block_number = block_data.number
                        
                        logger.info("New block detected",
                                   block_number=block_number,
                                   block_hash=block_hash.hex())
                        
                        # Store in database
                        await store_block(block_number, block_hash, block_data)
                    
                    # Small delay to prevent excessive polling
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error processing blocks on {ws_url}", error=str(e))
                    await asyncio.sleep(5)
                    break  # Try next endpoint
                    
        except Exception as e:
            logger.warning(f"Failed to connect to {ws_url}", error=str(e))
            try:
                if hasattr(provider, 'disconnect'):
                    await provider.disconnect()
            except:
                pass
            continue  # Try next WebSocket endpoint
    
    # If all WebSocket endpoints fail, use HTTP fallback
    logger.info("All WebSocket endpoints failed, falling back to HTTP polling")
    await fallback_http_listener()

async def fallback_http_listener():
    """HTTP-based block listener using public RPC endpoints."""
    # Try each public RPC endpoint
    for rpc_url in ARBITRUM_SEPOLIA_PUBLIC_RPCS:
        try:
            logger.info(f"Attempting HTTP connection to {rpc_url}")
            provider = AsyncHTTPProvider(rpc_url)
            w3 = AsyncWeb3(provider)
            
            # Test connection
            last_block = await w3.eth.block_number
            logger.info(f"Connected to {rpc_url}, starting from block {last_block}")
            
            while True:
                try:
                    current_block = await w3.eth.block_number
                    if current_block > last_block:
                        # Process new blocks
                        for block_num in range(last_block + 1, current_block + 1):
                            try:
                                block_data = await w3.eth.get_block(block_num)
                                logger.info("New block detected (HTTP)", block_number=block_num)
                                await store_block(block_num, block_data.hash, block_data)
                            except Exception as e:
                                logger.error(f"Error processing block {block_num}", error=str(e))
                        
                        last_block = current_block
                    
                    # Poll every 12 seconds (reasonable for Arbitrum)
                    await asyncio.sleep(12)
                    
                except Exception as e:
                    logger.error(f"HTTP polling error on {rpc_url}", error=str(e))
                    await asyncio.sleep(30)
                    break  # Try next RPC endpoint
                    
        except Exception as e:
            logger.warning(f"Failed to connect to {rpc_url}", error=str(e))
            continue  # Try next RPC endpoint
    
    logger.error("All RPC endpoints failed")
    raise Exception("No working RPC endpoints available")

def unix_timestamp_to_datetime(timestamp):
    """Convert Unix timestamp to UTC datetime object."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)

async def get_model_fields():
    """Get the actual field names from the BlockHeader model."""
    if hasattr(models.BlockHeader, '__table__'):
        return [col.name for col in models.BlockHeader.__table__.columns]
    return []

async def store_block(block_number, block_hash, block_data):
    async with AsyncSessionLocal() as session:
        try:
            existing_block = await session.get(models.BlockHeader, block_number)
            if existing_block:
                logger.debug("Block already exists", block_number=block_number)
                return

            model_fields = await get_model_fields()
            block_timestamp = unix_timestamp_to_datetime(block_data.timestamp)

            block_data_dict = {
                'block_number': block_number,
                'timestamp': block_timestamp.isoformat(),
                'hash': block_hash.hex() if hasattr(block_hash, 'hex') else str(block_hash),
                'transaction_count': len(block_data.transactions) if block_data.transactions else 0,
            }

            # filter fields
            valid_data = {k: v for k, v in block_data_dict.items() if k in model_fields}

            db_block = models.BlockHeader(**valid_data)
            session.add(db_block)
            await session.commit()

            logger.info("Block stored in database", block_number=block_number)

            # publish to Redis
            redis = await get_redis()
            await redis.publish("blocks", json.dumps(valid_data))

        except Exception as e:
            await session.rollback()
            logger.error("Failed to store block", block_number=block_number, error=str(e))

# Health check function to test endpoints
async def test_endpoints():
    """Test all available endpoints to see which ones are working."""
    logger.info("Testing available endpoints...")
    
    # Test HTTP endpoints
    for rpc_url in ARBITRUM_SEPOLIA_PUBLIC_RPCS:
        try:
            provider = AsyncHTTPProvider(rpc_url)
            w3 = AsyncWeb3(provider)
            block_number = await w3.eth.block_number
            logger.info(f"✓ {rpc_url} - Latest block: {block_number}")
        except Exception as e:
            logger.warning(f"✗ {rpc_url} - Error: {str(e)}")
    
    # Test WebSocket endpoints
    for ws_url in ARBITRUM_SEPOLIA_WS:
        try:
            provider = AsyncBaseProvider(ws_url)
            w3 = AsyncWeb3(provider)
            await w3.provider.connect()
            block_number = await w3.eth.block_number
            logger.info(f"✓ {ws_url} - Latest block: {block_number}")
            await w3.provider.disconnect()
        except Exception as e:
            logger.warning(f"✗ {ws_url} - Error: {str(e)}")

async def main():
    """Main function to run the block listener."""
    logger.info("Starting Arbitrum block listener with public endpoints...")
    
    # Optional: Test endpoints first
    # await test_endpoints()
    
    try:
        await listen_blocks()
    except KeyboardInterrupt:
        logger.info("Block listener stopped by user")
    except Exception as e:
        logger.error("Block listener failed", error=str(e))

if __name__ == "__main__":
    asyncio.run(main())