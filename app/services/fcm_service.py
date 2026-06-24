import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import asyncio
from jose import jwt
from datetime import datetime, timezone

from app.db.database import SessionLocal
from app.db.models import FCMToken, User
from app.services.object_storage import storage_service

class FCMService:
    def __init__(self):
        self._project_id = None
        self._service_account_info = None
        self._access_token = None
        self._token_expiry = 0
        
        # Load from .env or root
        sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if not sa_path:
            default_path = os.path.join(os.getcwd(), "firebase-service-account.json")
            if os.path.exists(default_path):
                sa_path = default_path
                
        if sa_path and os.path.exists(sa_path):
            try:
                with open(sa_path, "r", encoding="utf-8") as f:
                    self._service_account_info = json.load(f)
                self._project_id = self._service_account_info.get("project_id")
                print(f"[FCM Service] Loaded service account for project: {self._project_id}")
            except Exception as e:
                print(f"[FCM Service] Error loading service account JSON: {e}")
        else:
            print("[FCM Service] WARNING: Firebase service account JSON not found. Push notifications are disabled.")

    def _get_oauth2_token(self) -> str | None:
        if not self._service_account_info:
            return None
            
        now = int(time.time())
        # Cache token for up to 55 minutes (exp is 60 mins)
        if self._access_token and now < self._token_expiry - 300:
            return self._access_token
            
        try:
            payload = {
                "iss": self._service_account_info["client_email"],
                "scope": "https://www.googleapis.com/auth/firebase.messaging",
                "aud": "https://oauth2.googleapis.com/token",
                "exp": now + 3600,
                "iat": now
            }
            
            private_key = self._service_account_info["private_key"]
            signed_jwt = jwt.encode(payload, private_key, algorithm="RS256")
            
            data = urllib.parse.urlencode({
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": signed_jwt
            }).encode("utf-8")
            
            req = urllib.request.Request(
                "https://oauth2.googleapis.com/token",
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                self._access_token = res_data["access_token"]
                self._token_expiry = now + 3600
                return self._access_token
        except Exception as e:
            print(f"[FCM Service] Error generating OAuth2 access token: {e}")
            return None

    def _send_request_sync(self, fcm_token: str, title: str, body: str, data: dict = None) -> bool:
        access_token = self._get_oauth2_token()
        if not access_token or not self._project_id:
            return False
   
        url = f"https://fcm.googleapis.com/v1/projects/{self._project_id}/messages:send"
        
        payload = {
            "message": {
                "token": fcm_token,
                "notification": {
                    "title": title,
                    "body": body
                }
            }
        }
        
        if data:
            payload["message"]["data"] = {k: str(v) for k, v in data.items() if v is not None}
            
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res = json.loads(response.read().decode("utf-8"))
                return "name" in res
        except urllib.error.HTTPError as e:
            print(f"[FCM Service] HTTP Error sending FCM message to token {fcm_token[:15]}...: {e}")
            if e.code in (404, 410):
                self._delete_token_from_db(fcm_token)
            return False
        except Exception as e:
            print(f"[FCM Service] Error sending FCM message to token {fcm_token[:15]}...: {e}")
            return False

    def _delete_token_from_db(self, fcm_token: str):
        db = SessionLocal()
        try:
            db.query(FCMToken).filter(FCMToken.fld_token == fcm_token).delete()
            db.commit()
            print(f"[FCM Service] Removed invalid/unregistered token {fcm_token[:15]}... from database")
        except Exception as db_err:
            print(f"[FCM Service] Error removing invalid token {fcm_token[:15]}... from database: {db_err}")
        finally:
            db.close()

    async def send_notification(self, fcm_token: str, title: str, body: str, data: dict = None) -> bool:
        return await asyncio.to_thread(self._send_request_sync, fcm_token, title, body, data)

    async def send_multicast_notifications(self, fcm_tokens: list[str], title: str, body: str, data: dict = None):
        if not fcm_tokens:
            return
        tasks = [self.send_notification(token, title, body, data) for token in fcm_tokens]
        await asyncio.gather(*tasks, return_exceptions=True)

# Global instance
fcm_service = FCMService()

async def send_chat_notification(sender_id: int, recipient_ids: list[int], conversation_id: int, text: str, client_msg_id: str):
    db = SessionLocal()
    try:
        sender = db.query(User).filter(User.fld_user_id == sender_id).first()
        if not sender:
            return
            
        title = f"{sender.fld_firstname} {sender.fld_lastname}".strip()

        if not title:
            title = sender.fld_username
            
        body = text
        
        valid_recipients = [rid for rid in recipient_ids if rid != sender_id]
        if not valid_recipients:
            return
            
        tokens = db.query(FCMToken.fld_token).filter(FCMToken.fld_user_id.in_(valid_recipients)).all()
        token_list = [t[0] for t in tokens if t[0]]
        
        if not token_list:
            return
            
        data = {
            "chatId": str(conversation_id),
            "otherUserId": str(sender_id),
            "messageId": client_msg_id,
            "name": title,
            "avatarUrl": storage_service.get_public_avatar_url(sender.fld_avatar_url),
            "chatType": "individual"
        }
        
        await fcm_service.send_multicast_notifications(token_list, title, body, data)
    except Exception as e:
        print(f"[FCM Notification Wrapper] Error: {e}")
    finally:
        db.close()
