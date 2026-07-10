import json
from channels.generic.websocket import AsyncWebsocketConsumer


class DetectionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add('detections', self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard('detections', self.channel_name)

    async def detection_alert(self, event):
        await self.send(text_data=json.dumps({
            'type': 'detection',
            'nom': event.get('nom'),
            'prenom': event.get('prenom'),
            'matches': event.get('matches', []),
        }))
