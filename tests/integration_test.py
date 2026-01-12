"""
NATS Integration Test

Comprehensive test that demonstrates the full message flow:
1. Start mock agents
2. Simulate events
3. Verify request/reply patterns
4. Test parallel queries
"""

import asyncio
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from common.client import KioskNATSClient, NATSConfig
from common.message import NATSMessage, create_event, create_request


console = Console()


class IntegrationTest:
    """
    Integration test that verifies NATS communication patterns.
    """
    
    def __init__(self):
        self.client = KioskNATSClient(
            config=NATSConfig(name="integration-test")
        )
        self.session_id = "test-session-001"
        self.results = []
    
    async def run(self):
        """Run all integration tests."""
        console.print(Panel.fit(
            "[bold cyan]NATS Integration Test[/bold cyan]\n"
            "Testing component communication patterns",
            border_style="cyan"
        ))
        
        await self.client.connect()
        
        try:
            # Run tests
            await self.test_menu_search()
            await self.test_menu_details()
            await self.test_recsys_suggest()
            await self.test_parallel_requests()
            await self.test_pubsub_events()
            
            # Print results
            self.print_results()
            
        finally:
            await self.client.disconnect()
    
    def record_result(self, test_name: str, passed: bool, details: str = ""):
        """Record a test result."""
        self.results.append({
            "name": test_name,
            "passed": passed,
            "details": details
        })
    
    # ========================================
    # Test Cases
    # ========================================
    
    async def test_menu_search(self):
        """Test menu search request/reply."""
        console.print("\n[bold]Test 1: Menu Search[/bold]")
        
        request = create_request(
            command="search",
            payload={"query": "burger", "limit": 5},
            session_id=self.session_id
        )
        
        try:
            response = await self.client.request(
                "kiosk.agent.menu.search",
                request,
                timeout=5.0
            )
            
            items = response.payload.get("items", [])
            passed = (
                response.payload.get("status") == "success" and
                len(items) > 0
            )
            
            self.record_result(
                "Menu Search",
                passed,
                f"Found {len(items)} items"
            )
            
            if passed:
                console.print(f"  [green]✓[/green] Found {len(items)} items")
                for item in items[:3]:
                    console.print(f"    • {item['name']} - ${item['price']}")
            else:
                console.print(f"  [red]✗[/red] Search failed")
        
        except asyncio.TimeoutError:
            self.record_result("Menu Search", False, "Timeout")
            console.print("  [red]✗[/red] Timeout - is mock_menu_agent running?")
        except Exception as e:
            self.record_result("Menu Search", False, str(e))
            console.print(f"  [red]✗[/red] Error: {e}")
    
    async def test_menu_details(self):
        """Test menu details request/reply."""
        console.print("\n[bold]Test 2: Menu Details[/bold]")
        
        request = create_request(
            command="get_details",
            payload={"item_id": 101},
            session_id=self.session_id
        )
        
        try:
            response = await self.client.request(
                "kiosk.agent.menu.details",
                request,
                timeout=5.0
            )
            
            item = response.payload.get("item", {})
            passed = (
                response.payload.get("status") == "success" and
                item.get("name") is not None
            )
            
            self.record_result(
                "Menu Details",
                passed,
                f"Got {item.get('name', 'N/A')}"
            )
            
            if passed:
                console.print(f"  [green]✓[/green] Got item: {item['name']}")
                console.print(f"    Description: {item.get('description', 'N/A')[:50]}...")
            else:
                console.print(f"  [red]✗[/red] Details failed")
        
        except asyncio.TimeoutError:
            self.record_result("Menu Details", False, "Timeout")
            console.print("  [red]✗[/red] Timeout")
        except Exception as e:
            self.record_result("Menu Details", False, str(e))
            console.print(f"  [red]✗[/red] Error: {e}")
    
    async def test_recsys_suggest(self):
        """Test recommendation request/reply."""
        console.print("\n[bold]Test 3: Recommendations[/bold]")
        
        request = create_request(
            command="suggest",
            payload={
                "cart": [{"item_id": 101, "name": "Volcano Burger"}],
                "context": {"weather": "hot"}
            },
            session_id=self.session_id
        )
        
        try:
            response = await self.client.request(
                "kiosk.agent.recsys.suggest",
                request,
                timeout=5.0
            )
            
            suggestions = response.payload.get("suggestions", [])
            passed = response.payload.get("status") == "success"
            
            self.record_result(
                "Recommendations",
                passed,
                f"Got {len(suggestions)} suggestions"
            )
            
            if passed:
                console.print(f"  [green]✓[/green] Got {len(suggestions)} suggestions")
                for s in suggestions:
                    console.print(f"    • {s['name']}: {s['pitch']}")
            else:
                console.print(f"  [red]✗[/red] Suggestions failed")
        
        except asyncio.TimeoutError:
            self.record_result("Recommendations", False, "Timeout")
            console.print("  [red]✗[/red] Timeout - is mock_recsys_agent running?")
        except Exception as e:
            self.record_result("Recommendations", False, str(e))
            console.print(f"  [red]✗[/red] Error: {e}")
    
    async def test_parallel_requests(self):
        """Test parallel requests to multiple agents."""
        console.print("\n[bold]Test 4: Parallel Requests[/bold]")
        
        menu_request = create_request(
            command="search",
            payload={"query": "fries"},
            session_id=self.session_id
        )
        
        recsys_request = create_request(
            command="suggest",
            payload={"cart": [], "context": {}},
            session_id=self.session_id
        )
        
        try:
            import time
            start = time.time()
            
            # Execute in parallel
            menu_response, recsys_response = await asyncio.gather(
                self.client.request("kiosk.agent.menu.search", menu_request),
                self.client.request("kiosk.agent.recsys.suggest", recsys_request),
                return_exceptions=True
            )
            
            elapsed = time.time() - start
            
            menu_ok = (
                isinstance(menu_response, NATSMessage) and
                menu_response.payload.get("status") == "success"
            )
            recsys_ok = (
                isinstance(recsys_response, NATSMessage) and
                recsys_response.payload.get("status") == "success"
            )
            
            passed = menu_ok and recsys_ok
            
            self.record_result(
                "Parallel Requests",
                passed,
                f"Completed in {elapsed:.2f}s"
            )
            
            if passed:
                console.print(f"  [green]✓[/green] Both requests completed in {elapsed:.2f}s")
            else:
                console.print(f"  [red]✗[/red] One or more requests failed")
                if not menu_ok:
                    console.print(f"    Menu: {menu_response}")
                if not recsys_ok:
                    console.print(f"    Recsys: {recsys_response}")
        
        except Exception as e:
            self.record_result("Parallel Requests", False, str(e))
            console.print(f"  [red]✗[/red] Error: {e}")
    
    async def test_pubsub_events(self):
        """Test pub/sub event pattern."""
        console.print("\n[bold]Test 5: Pub/Sub Events[/bold]")
        
        received_events = []
        
        async def event_handler(msg: NATSMessage, subject: str):
            received_events.append((subject, msg))
        
        # Subscribe
        await self.client.subscribe("kiosk.test.>", event_handler)
        
        # Give subscription time to establish
        await asyncio.sleep(0.1)
        
        # Publish test events
        for i in range(3):
            event = create_event(
                event_type="test_event",
                payload={"index": i},
                session_id=self.session_id
            )
            await self.client.publish(f"kiosk.test.event_{i}", event)
        
        # Wait for events to be received
        await asyncio.sleep(0.5)
        
        passed = len(received_events) == 3
        
        self.record_result(
            "Pub/Sub Events",
            passed,
            f"Received {len(received_events)}/3 events"
        )
        
        if passed:
            console.print(f"  [green]✓[/green] Received all 3 events")
        else:
            console.print(f"  [red]✗[/red] Received {len(received_events)}/3 events")
    
    # ========================================
    # Results
    # ========================================
    
    def print_results(self):
        """Print test results summary."""
        console.print("\n")
        
        table = Table(title="Test Results", show_header=True)
        table.add_column("Test", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        
        passed_count = 0
        for result in self.results:
            status = "[green]PASS[/green]" if result["passed"] else "[red]FAIL[/red]"
            table.add_row(result["name"], status, result["details"])
            if result["passed"]:
                passed_count += 1
        
        console.print(table)
        
        total = len(self.results)
        console.print(f"\n[bold]Summary: {passed_count}/{total} tests passed[/bold]")
        
        if passed_count == total:
            console.print("[green]All tests passed! ✓[/green]")
        else:
            console.print("[red]Some tests failed. Check if all mock agents are running.[/red]")


async def main():
    """Run integration tests."""
    # Check if help requested
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print("""
NATS Integration Test

Usage:
  python -m tests.integration_test

Prerequisites:
  1. Start NATS server:
     docker-compose up -d nats
  
  2. Start mock agents (in separate terminals):
     python -m tests.mock_menu_agent
     python -m tests.mock_recsys_agent

  3. Run this test:
     python -m tests.integration_test
        """)
        return
    
    test = IntegrationTest()
    await test.run()


if __name__ == "__main__":
    asyncio.run(main())
