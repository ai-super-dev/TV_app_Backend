from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from uvicorn.protocols.utils import ClientDisconnected
from typing import List, Dict
import json
from sqlalchemy.orm import Session
from database import get_db
import models
from sqlalchemy.exc import SQLAlchemyError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_count = 0
        self.db: Session = next(get_db())  # Get database session

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        client_id = str(self.connection_count)
        self.active_connections[client_id] = websocket
        self.connection_count += 1
        return client_id

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            self.broadcast(f"Client {client_id} disconnected")

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast(self, message: str):
        for client_id, connection in self.active_connections.items():
            try:
                await connection.send_text(message)
            except (ClientDisconnected, WebSocketDisconnect):
                logger.warning(f"Client {client_id} disconnected unexpectedly")
                self.disconnect(client_id)
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")
                self.disconnect(client_id)

    async def handle_device_connect(self, device_id: str) -> dict:
        # Check if device exists
        device = self.db.query(models.Device).filter(models.Device.device_id == device_id).first()
        if not device_id:
            return None
        
        if device:
            # Update existing device status but keep is_active unchanged
            device.status = models.DeviceStatus.ONLINE
            self.db.commit()
            action = "updated"
        else:
            # Create new device
            device = models.Device(
                device_id=device_id, 
                status=models.DeviceStatus.ONLINE,
                is_active=False  # Default to inactive
            )
            self.db.add(device)
            self.db.commit()
            self.db.refresh(device)
            action = "created"

        # Return current device state including is_active
        return {
            "type": "device_update",
            "action": action,
            "device": {
                "id": device.id,
                "device_id": device.device_id,
                "is_active": device.is_active,
                "status": device.status
            }
        }
 
    async def handle_device_disconnect(self, device_id: str) -> dict:
        # Find and update device status in database
        device = self.db.query(models.Device).filter(models.Device.device_id == device_id).first()
        
        if device:
            device.status = models.DeviceStatus.OFFLINE
            self.db.commit()
            
            return {
                "type": "device_update",
                "action": "disconnected",
                "device": {
                    "id": device.id,
                    "device_id": device.device_id,
                    "is_active": device.is_active,
                    "status": device.status
                }
            }
        return None

    async def handle_websocket_disconnect(self, client_id: str):
        await self.disconnect(client_id)
        await self.broadcast(
            json.dumps({
                "type": "user_left",
                "client_id": client_id,
                "message": f"Client {client_id} left"
            })
        )

    async def handle_lesson_state_change(self, device_id: str, is_active: bool) -> dict:
        # Update device state in database
        try:
            # Start a new transaction
            device = self.db.query(models.Device).filter(models.Device.device_id == device_id).first()
            
            if device:
                device.is_active = is_active
                self.db.commit()
                
                return {
                    "type": "lesson_state_update",
                    "device": {
                        "id": device.id,
                        "device_id": device.device_id,
                        "is_active": device.is_active,
                        "status": device.status
                    }
                }
            
        except SQLAlchemyError as e:
            # Rollback the transaction in case of an error
            self.db.rollback()
            # Log the error or handle it as needed
            raise e
        finally:
            # Optionally, close the session if you're done with it
            self.db.close()
        
        
        return None

manager = ConnectionManager()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    client_id = await manager.connect(websocket)
    try:
        # Send welcome message
        await manager.send_personal_message(
            json.dumps({
                "type": "connection_established",
                "client_id": client_id,
                "message": "Connected to server"
            }),
            client_id
        )
        
        # Broadcast new connection
        # await manager.broadcast(
        #     json.dumps({
        #         "type": "user_joined",
        #         "client_id": client_id,
        #         "message": f"Client {client_id} joined"
        #     }),
        #     exclude=client_id
        # )

        while True:
            try:
                data = await websocket.receive_text()
                message_data = json.loads(data)
                print(f"Received WebSocket message: {message_data}")
                print(f"{message_data}: {message_data.get("type") == "lesson_state_change"}")

                if message_data.get("type") == "device_connect":
                    # Handle device connection
                    device_update = await manager.handle_device_connect(message_data["deviceId"])
                    # Broadcast device update to all clients
                    await manager.broadcast(json.dumps(device_update))
                elif message_data.get("type") == "device_disconnect":
                    device_update = await manager.handle_device_disconnect(message_data["deviceId"])
                    if device_update:
                        await manager.broadcast(json.dumps(device_update))
                elif message_data.get("type") == "lesson_state_change":
                    
                    state_update = await manager.handle_lesson_state_change(
                        message_data["deviceId"],
                        message_data["isActive"]
                    )
                    if state_update:
                        await manager.broadcast(json.dumps(state_update))
                else:
                    # Handle other message types
                    message_data["client_id"] = client_id
                    await manager.broadcast(json.dumps(message_data))

            except json.JSONDecodeError:
                await manager.broadcast(
                    json.dumps({
                        "type": "message",
                        "client_id": client_id,
                        "message": data
                    })
                )

    except WebSocketDisconnect:
        await manager.handle_websocket_disconnect(client_id) 
    except Exception as e:
        logger.error(f"Error in WebSocket connection: {e}")
        await manager.handle_websocket_disconnect(client_id) 