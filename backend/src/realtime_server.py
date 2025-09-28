"""
Production-ready real-time WebSocket server for Skylapse mountain camera system.
Replaces broken Socket.IO implementation with robust, authenticated WebSocket connections.
"""

import asyncio
import json
import logging
import traceback
import uuid
import weakref
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import aiohttp
import jwt
from aiohttp import WSMsgType, web
from aiohttp.web_ws import WebSocketResponse

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = "skylapse_jwt_secret_change_in_production"  # TODO: Move to environment
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24


class ConnectionManager:
    """Manages WebSocket connections with authentication and health monitoring."""

    def __init__(self):
        self.connections: Dict[str, WebSocketResponse] = {}
        self.subscriptions: Dict[str, Set[str]] = {}  # channel -> set of connection_ids
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        self.connection_health: Dict[str, datetime] = {}

    async def add_connection(
        self, connection_id: str, ws: WebSocketResponse, user_info: Dict[str, Any]
    ) -> None:
        """Add authenticated connection."""
        self.connections[connection_id] = ws
        self.connection_metadata[connection_id] = {
            "user_info": user_info,
            "connected_at": datetime.now(),
            "ip_address": ws._request.remote,
            "user_agent": ws._request.headers.get("User-Agent", "Unknown"),
        }
        self.connection_health[connection_id] = datetime.now()

        logger.info(
            f"WebSocket connection added: {connection_id} for user {user_info.get('user_id', 'unknown')}"
        )

    async def remove_connection(self, connection_id: str) -> None:
        """Remove connection and clean up subscriptions."""
        if connection_id in self.connections:
            del self.connections[connection_id]

        if connection_id in self.connection_metadata:
            user_info = self.connection_metadata[connection_id]["user_info"]
            logger.info(
                f"WebSocket connection removed: {connection_id} for user {user_info.get('user_id', 'unknown')}"
            )
            del self.connection_metadata[connection_id]

        if connection_id in self.connection_health:
            del self.connection_health[connection_id]

        # Remove from all subscriptions
        for channel, subscribers in self.subscriptions.items():
            subscribers.discard(connection_id)

    async def subscribe(self, connection_id: str, channel: str) -> bool:
        """Subscribe connection to a channel."""
        if connection_id not in self.connections:
            return False

        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()

        self.subscriptions[channel].add(connection_id)
        logger.debug(f"Connection {connection_id} subscribed to channel: {channel}")
        return True

    async def unsubscribe(self, connection_id: str, channel: str) -> bool:
        """Unsubscribe connection from a channel."""
        if channel in self.subscriptions:
            self.subscriptions[channel].discard(connection_id)
            logger.debug(f"Connection {connection_id} unsubscribed from channel: {channel}")
            return True
        return False

    async def broadcast_to_channel(self, channel: str, message: Dict[str, Any]) -> int:
        """Broadcast message to all subscribers of a channel."""
        if channel not in self.subscriptions:
            return 0

        message_json = json.dumps(message)
        sent_count = 0
        dead_connections = []

        for connection_id in self.subscriptions[channel].copy():
            if connection_id not in self.connections:
                dead_connections.append(connection_id)
                continue

            try:
                ws = self.connections[connection_id]
                if ws.closed:
                    dead_connections.append(connection_id)
                    continue

                await ws.send_str(message_json)
                sent_count += 1
                self.connection_health[connection_id] = datetime.now()

            except Exception as e:
                logger.warning(f"Failed to send message to connection {connection_id}: {e}")
                dead_connections.append(connection_id)

        # Clean up dead connections
        for connection_id in dead_connections:
            await self.remove_connection(connection_id)

        if sent_count > 0:
            logger.debug(f"Broadcast to channel '{channel}': {sent_count} recipients")

        return sent_count

    async def send_to_connection(self, connection_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific connection."""
        if connection_id not in self.connections:
            return False

        try:
            ws = self.connections[connection_id]
            if ws.closed:
                await self.remove_connection(connection_id)
                return False

            await ws.send_str(json.dumps(message))
            self.connection_health[connection_id] = datetime.now()
            return True

        except Exception as e:
            logger.warning(f"Failed to send message to connection {connection_id}: {e}")
            await self.remove_connection(connection_id)
            return False

    async def ping_connections(self) -> None:
        """Send ping to all connections to check health."""
        ping_message = {"type": "ping", "timestamp": datetime.now().isoformat()}

        dead_connections = []
        for connection_id, ws in self.connections.items():
            try:
                if ws.closed:
                    dead_connections.append(connection_id)
                    continue

                await ws.ping()

            except Exception as e:
                logger.warning(f"Ping failed for connection {connection_id}: {e}")
                dead_connections.append(connection_id)

        # Clean up dead connections
        for connection_id in dead_connections:
            await self.remove_connection(connection_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        now = datetime.now()
        healthy_connections = sum(
            1
            for last_seen in self.connection_health.values()
            if (now - last_seen).total_seconds() < 300  # 5 minutes
        )

        return {
            "total_connections": len(self.connections),
            "healthy_connections": healthy_connections,
            "channels": {
                channel: len(subscribers) for channel, subscribers in self.subscriptions.items()
            },
            "connection_details": [
                {
                    "connection_id": conn_id,
                    "user_id": metadata["user_info"].get("user_id"),
                    "connected_at": metadata["connected_at"].isoformat(),
                    "ip_address": metadata["ip_address"],
                    "last_seen": self.connection_health.get(conn_id, datetime.min).isoformat(),
                }
                for conn_id, metadata in self.connection_metadata.items()
            ],
        }


class JWTAuthenticator:
    """Handles JWT authentication for WebSocket connections."""

    @staticmethod
    def generate_token(user_id: str, permissions: List[str] = None) -> str:
        """Generate JWT token for user."""
        if permissions is None:
            permissions = ["dashboard:read", "camera:read"]

        payload = {
            "user_id": user_id,
            "permissions": permissions,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        }

        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token and return payload."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None


class SkylapsRealTimeServer:
    """Production-ready real-time server for Skylapse mountain camera system."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8082):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.connection_manager = ConnectionManager()
        self.authenticator = JWTAuthenticator()
        self._setup_routes()
        self._setup_middleware()

        # Background tasks
        self._health_check_task = None

    def _setup_routes(self) -> None:
        """Setup HTTP routes."""
        # WebSocket endpoint
        self.app.router.add_get("/ws", self._websocket_handler)

        # Authentication endpoints
        self.app.router.add_post("/auth/token", self._generate_token)

        # Health and monitoring
        self.app.router.add_get("/health", self._health_check)
        self.app.router.add_get("/stats", self._connection_stats)

        # Test endpoints for development
        self.app.router.add_post("/broadcast", self._test_broadcast)

    def _setup_middleware(self) -> None:
        """Setup middleware."""

        @web.middleware
        async def cors_middleware(request, handler):
            """CORS middleware for cross-origin requests."""
            if request.method == "OPTIONS":
                response = web.Response()
            else:
                response = await handler(request)

            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
            return response

        @web.middleware
        async def error_middleware(request, handler):
            """Error handling middleware."""
            try:
                return await handler(request)
            except Exception as e:
                logger.error(f"Request error: {e}\n{traceback.format_exc()}")
                return web.json_response(
                    {
                        "error": str(e),
                        "type": type(e).__name__,
                        "timestamp": datetime.now().isoformat(),
                    },
                    status=500,
                )

        self.app.middlewares.append(cors_middleware)
        self.app.middlewares.append(error_middleware)

    async def _websocket_handler(self, request) -> WebSocketResponse:
        """Handle WebSocket connections with authentication."""
        ws = WebSocketResponse(heartbeat=30)
        await ws.prepare(request)

        connection_id = str(uuid.uuid4())
        authenticated = False
        user_info = None

        try:
            # Wait for authentication message
            auth_timeout = 10  # 10 seconds to authenticate
            auth_message = await asyncio.wait_for(ws.receive(), timeout=auth_timeout)

            if auth_message.type != WSMsgType.TEXT:
                await ws.send_str(
                    json.dumps(
                        {
                            "type": "auth_error",
                            "error": "First message must be text containing authentication",
                        }
                    )
                )
                return ws

            try:
                auth_data = json.loads(auth_message.data)
            except json.JSONDecodeError:
                await ws.send_str(
                    json.dumps(
                        {"type": "auth_error", "error": "Invalid JSON in authentication message"}
                    )
                )
                return ws

            # Verify JWT token
            token = auth_data.get("token")
            if not token:
                await ws.send_str(
                    json.dumps({"type": "auth_error", "error": "Missing authentication token"})
                )
                return ws

            user_info = self.authenticator.verify_token(token)
            if not user_info:
                await ws.send_str(
                    json.dumps(
                        {"type": "auth_error", "error": "Invalid or expired authentication token"}
                    )
                )
                return ws

            # Authentication successful
            authenticated = True
            await self.connection_manager.add_connection(connection_id, ws, user_info)

            # Send authentication success
            await ws.send_str(
                json.dumps(
                    {
                        "type": "auth_success",
                        "connection_id": connection_id,
                        "user_id": user_info["user_id"],
                        "permissions": user_info.get("permissions", []),
                    }
                )
            )

            # Handle subsequent messages
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await self._handle_message(connection_id, msg.data)
                elif msg.type == WSMsgType.ERROR:
                    logger.error(
                        f"WebSocket error for connection {connection_id}: {ws.exception()}"
                    )
                    break
                elif msg.type == WSMsgType.CLOSE:
                    logger.info(f"WebSocket closed for connection {connection_id}")
                    break

        except asyncio.TimeoutError:
            logger.warning(f"Authentication timeout for connection {connection_id}")
            await ws.send_str(json.dumps({"type": "auth_error", "error": "Authentication timeout"}))

        except Exception as e:
            logger.error(f"WebSocket handler error for connection {connection_id}: {e}")

        finally:
            if authenticated:
                await self.connection_manager.remove_connection(connection_id)

        return ws

    async def _handle_message(self, connection_id: str, message_data: str) -> None:
        """Handle incoming WebSocket message."""
        try:
            message = json.loads(message_data)
            message_type = message.get("type")

            if message_type == "subscribe":
                channel = message.get("channel")
                if channel:
                    success = await self.connection_manager.subscribe(connection_id, channel)
                    await self.connection_manager.send_to_connection(
                        connection_id,
                        {"type": "subscription_result", "channel": channel, "success": success},
                    )

                    # Send initial data for dashboard channel
                    if success and channel == "dashboard":
                        await self._send_initial_dashboard_data(connection_id)

            elif message_type == "unsubscribe":
                channel = message.get("channel")
                if channel:
                    success = await self.connection_manager.unsubscribe(connection_id, channel)
                    await self.connection_manager.send_to_connection(
                        connection_id,
                        {"type": "unsubscription_result", "channel": channel, "success": success},
                    )

            elif message_type == "pong":
                # Update health timestamp
                self.connection_manager.connection_health[connection_id] = datetime.now()

            else:
                logger.warning(
                    f"Unknown message type from connection {connection_id}: {message_type}"
                )

        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from connection {connection_id}: {message_data}")
        except Exception as e:
            logger.error(f"Error handling message from connection {connection_id}: {e}")

    async def _send_initial_dashboard_data(self, connection_id: str) -> None:
        """Send initial dashboard data to newly subscribed connection."""
        # TODO: Integrate with actual data sources
        initial_data = {
            "type": "dashboard_event",
            "event": "system.status",
            "data": {
                "service": {"capture": "running", "processing": "running", "camera": "connected"},
                "camera": {
                    "isConnected": True,
                    "model": "Arducam IMX519 16MP",
                    "resolution": {"width": 4656, "height": 3496},
                },
                "storage": {
                    "used": 50 * 1024 * 1024 * 1024,  # 50GB
                    "total": 500 * 1024 * 1024 * 1024,  # 500GB
                    "percentage": 10,
                },
            },
            "timestamp": datetime.now().isoformat(),
        }

        await self.connection_manager.send_to_connection(connection_id, initial_data)

    async def _generate_token(self, request) -> web.Response:
        """Generate JWT token (for development/testing)."""
        try:
            data = await request.json()
            user_id = data.get("user_id", "anonymous")
            permissions = data.get("permissions", ["dashboard:read", "camera:read"])

            token = self.authenticator.generate_token(user_id, permissions)

            return web.json_response(
                {"token": token, "user_id": user_id, "expires_in": JWT_EXPIRY_HOURS * 3600}
            )

        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def _health_check(self, request) -> web.Response:
        """Health check endpoint."""
        stats = self.connection_manager.get_stats()

        return web.json_response(
            {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0-production",
                "connections": stats["total_connections"],
                "healthy_connections": stats["healthy_connections"],
            }
        )

    async def _connection_stats(self, request) -> web.Response:
        """Detailed connection statistics."""
        return web.json_response(self.connection_manager.get_stats())

    async def _test_broadcast(self, request) -> web.Response:
        """Test broadcast endpoint for development."""
        try:
            data = await request.json()
            channel = data.get("channel", "dashboard")
            message = data.get("message", {})

            sent_count = await self.connection_manager.broadcast_to_channel(channel, message)

            return web.json_response({"sent_to": sent_count, "channel": channel})

        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def _health_check_background(self) -> None:
        """Background task for connection health monitoring."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                await self.connection_manager.ping_connections()

                stats = self.connection_manager.get_stats()
                logger.debug(
                    f"Connection health check: {stats['healthy_connections']}/{stats['total_connections']} healthy"
                )

            except Exception as e:
                logger.error(f"Health check background task error: {e}")

    async def start(self) -> None:
        """Start the real-time server."""
        logger.info(f"Starting Skylapse real-time server on {self.host}:{self.port}")

        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()

            # Start background tasks
            self._health_check_task = asyncio.create_task(self._health_check_background())

            logger.info(f"Skylapse real-time server started on http://{self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start real-time server: {e}")
            raise

    async def shutdown(self) -> None:
        """Shutdown the real-time server."""
        logger.info("Shutting down Skylapse real-time server")

        try:
            # Cancel background tasks
            if self._health_check_task:
                self._health_check_task.cancel()
                try:
                    await self._health_check_task
                except asyncio.CancelledError:
                    pass

            # Close all WebSocket connections
            for connection_id in list(self.connection_manager.connections.keys()):
                await self.connection_manager.remove_connection(connection_id)

            # Shutdown HTTP server
            if self.site:
                await self.site.stop()

            if self.runner:
                await self.runner.cleanup()

            logger.info("Skylapse real-time server shutdown complete")

        except Exception as e:
            logger.error(f"Error during real-time server shutdown: {e}")

    async def broadcast_dashboard_event(self, event_type: str, data: Dict[str, Any]) -> int:
        """Broadcast dashboard event to all subscribers."""
        message = {
            "type": "dashboard_event",
            "event": event_type,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }

        return await self.connection_manager.broadcast_to_channel("dashboard", message)


# Standalone server entry point
async def main():
    """Run standalone real-time server."""
    import os

    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Get configuration from environment
    host = os.getenv("REALTIME_HOST", "0.0.0.0")
    port = int(os.getenv("REALTIME_PORT", 8082))

    server = SkylapsRealTimeServer(host, port)

    try:
        await server.start()

        # Keep server running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
