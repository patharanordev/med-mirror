
import asyncio
import sys
import os

# Add agent directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.agent_graph import agent_service

async def main():
    print("Starting verification of warmup...")
    try:
        await agent_service.warmup()
        print("Verification SUCCESS: Warmup completed without errors.")
    except Exception as e:
        print(f"Verification FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(main())
