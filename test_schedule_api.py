#!/usr/bin/env python3
"""Test script for schedule management API endpoints."""

import asyncio
import json
import sys
from datetime import datetime

import aiohttp


async def test_schedule_api():
    """Test the schedule management API endpoints."""
    base_url = "http://helios.local:8080/api/schedule"

    async with aiohttp.ClientSession() as session:
        print("🧪 Testing Schedule Management API")
        print("=" * 50)

        # Test 1: Get all schedules (should be empty initially)
        print("\n1. GET /api/schedule - Get all schedules")
        try:
            async with session.get(base_url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Success: Found {data.get('total', 0)} schedules")
                    print(f"   Response: {json.dumps(data, indent=2)}")
                else:
                    print(f"❌ Failed: HTTP {response.status}")
                    print(f"   Response: {await response.text()}")
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return

        # Test 2: Create a new schedule
        print("\n2. POST /api/schedule - Create new schedule")
        test_schedule = {
            "name": "Test Golden Hour Schedule",
            "description": "Automated testing schedule for golden hour captures",
            "enabled": True,
            "startTime": "06:00",
            "endTime": "08:00",
            "intervalMinutes": 5,
            "daysOfWeek": [1, 2, 3, 4, 5],  # Monday to Friday
            "captureSettings": {"preset": "golden_hour"},
            "conditions": {"weatherDependent": True, "minLightLevel": 10.0, "maxWindSpeed": 20.0},
        }

        try:
            async with session.post(base_url, json=test_schedule) as response:
                if response.status == 201:
                    data = await response.json()
                    schedule_id = data["data"]["id"]
                    print(f"✅ Success: Created schedule with ID {schedule_id}")
                    print(f"   Name: {data['data']['name']}")
                    print(f"   Next execution: {data['data'].get('nextExecution', 'None')}")
                else:
                    print(f"❌ Failed: HTTP {response.status}")
                    print(f"   Response: {await response.text()}")
                    return
        except Exception as e:
            print(f"❌ Error: {e}")
            return

        # Test 3: Get the specific schedule
        print(f"\n3. GET /api/schedule/{schedule_id} - Get specific schedule")
        try:
            async with session.get(f"{base_url}/{schedule_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Success: Retrieved schedule '{data['data']['name']}'")
                    print(f"   Status: {data['data']['status']}")
                    print(f"   Enabled: {data['data']['enabled']}")
                else:
                    print(f"❌ Failed: HTTP {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test 4: Update the schedule
        print(f"\n4. PUT /api/schedule/{schedule_id} - Update schedule")
        update_data = {
            "name": "Updated Test Schedule",
            "description": "Updated description for testing",
            "intervalMinutes": 10,
            "enabled": False,
        }

        try:
            async with session.put(f"{base_url}/{schedule_id}", json=update_data) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Success: Updated schedule")
                    print(f"   New name: {data['data']['name']}")
                    print(f"   New interval: {data['data']['intervalMinutes']} minutes")
                    print(f"   Enabled: {data['data']['enabled']}")
                else:
                    print(f"❌ Failed: HTTP {response.status}")
                    print(f"   Response: {await response.text()}")
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test 5: Get all schedules again (should show our schedule)
        print("\n5. GET /api/schedule - Get all schedules (after creation)")
        try:
            async with session.get(base_url) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Success: Found {data.get('total', 0)} schedules")
                    for schedule in data.get("data", []):
                        print(
                            f"   - {schedule['name']} (ID: {schedule['id']}, Status: {schedule['status']})"
                        )
                else:
                    print(f"❌ Failed: HTTP {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test 6: Test validation by creating invalid schedule
        print("\n6. POST /api/schedule - Test validation (should fail)")
        invalid_schedule = {
            "name": "",  # Invalid: empty name
            "startTime": "25:00",  # Invalid: bad time format
            "intervalMinutes": -5,  # Invalid: negative interval
        }

        try:
            async with session.post(base_url, json=invalid_schedule) as response:
                if response.status == 400:
                    data = await response.json()
                    print(f"✅ Success: Validation correctly rejected invalid data")
                    print(f"   Error: {data.get('error', 'No error message')}")
                else:
                    print(f"❌ Unexpected: Expected 400, got {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test 7: Delete the schedule
        print(f"\n7. DELETE /api/schedule/{schedule_id} - Delete schedule")
        try:
            async with session.delete(f"{base_url}/{schedule_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Success: Deleted schedule")
                    print(f"   Message: {data.get('message', 'No message')}")
                else:
                    print(f"❌ Failed: HTTP {response.status}")
                    print(f"   Response: {await response.text()}")
        except Exception as e:
            print(f"❌ Error: {e}")

        # Test 8: Try to get deleted schedule (should fail)
        print(f"\n8. GET /api/schedule/{schedule_id} - Get deleted schedule (should fail)")
        try:
            async with session.get(f"{base_url}/{schedule_id}") as response:
                if response.status == 404:
                    print(f"✅ Success: Correctly returned 404 for deleted schedule")
                else:
                    print(f"❌ Unexpected: Expected 404, got {response.status}")
        except Exception as e:
            print(f"❌ Error: {e}")

        print("\n" + "=" * 50)
        print("🎉 Schedule API testing completed!")


async def test_health_check():
    """Test if the capture service is running."""
    print("🔍 Checking if capture service is running...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://helios.local:8080/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"✅ Capture service is healthy: {data.get('status', 'unknown')}")
                    return True
                else:
                    print(f"❌ Capture service health check failed: HTTP {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Cannot connect to capture service: {e}")
        print("   Make sure the capture service is running on helios.local:8080")
        return False


async def main():
    """Main test function."""
    print("Schedule Management API Test Suite")
    print(f"Time: {datetime.now().isoformat()}")
    print("Target: http://helios.local:8080/api/schedule")

    # Check if service is running
    if not await test_health_check():
        print("\n❌ Cannot proceed with tests - capture service is not available")
        sys.exit(1)

    # Run the actual tests
    await test_schedule_api()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)
