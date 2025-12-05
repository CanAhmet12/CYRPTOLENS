"""
Firebase Cloud Messaging Service
Handles sending push notifications via FCM.
"""
import os
import json
from typing import List, Optional, Dict
import logging

# Firebase Admin SDK will be imported if available
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logging.warning("firebase-admin not installed. Push notifications will not work.")


class FCMService:
    """Service for sending FCM notifications."""
    
    def __init__(self):
        self._initialized = False
        if FIREBASE_AVAILABLE:
            self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK."""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Try to get service account key from environment
                service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
                
                if service_account_path and os.path.exists(service_account_path):
                    cred = credentials.Certificate(service_account_path)
                    firebase_admin.initialize_app(cred)
                    self._initialized = True
                    logging.info("✅ Firebase Admin SDK initialized")
                else:
                    # Try to get from environment variable as JSON string
                    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
                    if service_account_json:
                        cred_info = json.loads(service_account_json)
                        cred = credentials.Certificate(cred_info)
                        firebase_admin.initialize_app(cred)
                        self._initialized = True
                        logging.info("✅ Firebase Admin SDK initialized from JSON")
                    else:
                        logging.warning("⚠️ Firebase service account not found. Push notifications disabled.")
            else:
                self._initialized = True
                logging.info("✅ Firebase Admin SDK already initialized")
        except Exception as e:
            logging.error(f"❌ Failed to initialize Firebase: {e}")
            self._initialized = False
    
    def is_available(self) -> bool:
        """Check if FCM service is available."""
        return FIREBASE_AVAILABLE and self._initialized
    
    def send_notification(
        self,
        fcm_token: str,
        title: str,
        body: str,
        data: Optional[Dict] = None,
        notification_type: str = "alert"
    ) -> bool:
        """
        Send a push notification to a single device.
        
        Args:
            fcm_token: FCM token of the target device
            title: Notification title
            body: Notification body
            data: Additional data payload
            notification_type: Type of notification (alert, market, portfolio)
        
        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.is_available():
            logging.warning("⚠️ FCM service not available. Notification not sent.")
            return False
        
        try:
            message = messaging.Message(
                token=fcm_token,
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data={
                    "type": notification_type,
                    **(data or {}),
                },
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        channel_id="cryptolens_alerts",
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                        ),
                    ),
                ),
            )
            
            response = messaging.send(message)
            logging.info(f"✅ Notification sent successfully: {response}")
            return True
            
        except messaging.UnregisteredError:
            logging.warning(f"⚠️ FCM token is unregistered: {fcm_token[:20]}...")
            return False
        except Exception as e:
            logging.error(f"❌ Failed to send notification: {e}")
            return False
    
    def send_multicast_notification(
        self,
        fcm_tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict] = None,
        notification_type: str = "alert"
    ) -> Dict[str, int]:
        """
        Send push notification to multiple devices.
        
        Returns:
            dict with 'success_count' and 'failure_count'
        """
        if not self.is_available():
            logging.warning("⚠️ FCM service not available. Notifications not sent.")
            return {"success_count": 0, "failure_count": len(fcm_tokens)}
        
        if not fcm_tokens:
            return {"success_count": 0, "failure_count": 0}
        
        try:
            message = messaging.MulticastMessage(
                tokens=fcm_tokens,
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data={
                    "type": notification_type,
                    **(data or {}),
                },
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        sound="default",
                        channel_id="cryptolens_alerts",
                    ),
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound="default",
                            badge=1,
                        ),
                    ),
                ),
            )
            
            response = messaging.send_multicast(message)
            
            # Remove invalid tokens
            if response.failure_count > 0:
                invalid_tokens = []
                for idx, result in enumerate(response.responses):
                    if not result.success:
                        if result.exception and isinstance(result.exception, messaging.UnregisteredError):
                            invalid_tokens.append(fcm_tokens[idx])
                
                if invalid_tokens:
                    logging.warning(f"⚠️ Found {len(invalid_tokens)} invalid FCM tokens")
                    # Return invalid tokens so they can be removed by the caller
                    # The caller should have database session access
                    return {
                        "success_count": response.success_count,
                        "failure_count": response.failure_count,
                        "invalid_tokens": invalid_tokens,
                    }
            
            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
            }
            
        except Exception as e:
            logging.error(f"❌ Failed to send multicast notification: {e}")
            return {"success_count": 0, "failure_count": len(fcm_tokens)}

