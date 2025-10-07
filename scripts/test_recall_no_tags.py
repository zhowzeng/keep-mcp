#!/usr/bin/env python3
"""Simple test script to verify FastMCP recall tool accepts no tags."""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from keep_mcp.application import build_application


async def main():
    """Test recall with and without tags."""
    db_path = Path("data/cards.db")
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return

    app = build_application(db_path)
    try:
        # First add a test card
        print("\n1. Adding test card...")
        add_result = await app.card_service.add_card(
            {
                "title": "Test card for recall",
                "summary": "This is a test card to verify recall works without tags.",
            }
        )
        print(f"   Added card: {add_result['cardId']}")

        # Test recall without tags (empty list)
        print("\n2. Testing recall with empty tags list...")
        result1 = await app.card_service.recall(
            query="test card",
            tags=[],
            limit=5,
            include_archived=False,
        )
        print(f"   Found {len(result1['cards'])} cards")

        # Test recall with no query and no tags
        print("\n3. Testing recall with no query and empty tags...")
        result2 = await app.card_service.recall(
            query=None,
            tags=[],
            limit=5,
            include_archived=False,
        )
        print(f"   Found {len(result2['cards'])} cards")

        # Test recall with query but no tags parameter
        print("\n4. Testing recall with query only...")
        result3 = await app.card_service.recall(
            query="test",
            tags=[],
            limit=5,
            include_archived=False,
        )
        print(f"   Found {len(result3['cards'])} cards")

        print("\n✅ All recall scenarios work correctly!")

    finally:
        app.connection_close()


if __name__ == "__main__":
    asyncio.run(main())
