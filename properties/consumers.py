import json
from channels.generic.websocket import AsyncWebsocketConsumer


class PropertyConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.property_id = self.scope['url_route']['kwargs']['property_id']
        self.group_name = f'property_{self.property_id}'

        # Join group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'property_update',
                'message': message
            }
        )

    # Receive message from group
    async def property_update(self, event):
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'property_update',
            'message': message
        }))
