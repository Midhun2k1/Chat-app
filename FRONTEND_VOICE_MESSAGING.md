# PingBee — Frontend Voice Messaging Integration Guide

This guide details how to implement the frontend voice messaging logic in the React Native mobile application to integrate with the completed PingBee backend.

---

## 1. Flow Overview

```
[ User Holds Mic ] ──► Record audio (AAC/.mp4/.wav)
                              │
[ User Releases ]  ──► Stop recording → Obtain local file URI
                              │
                      Upload to Server (multipart/form-data)
                      POST /messages/upload-audio
                      Headers: Authorization: Bearer <token>
                      Body: file=<audio file>, duration_seconds=<duration>
                              │
                      Server returns { audio_url, duration_seconds }
                              │
                      Send WebSocket Event
                      SEND_MSG with type: "audio"
                              │
                      Broadcasted to all chat participants
```

---

## 2. Dependencies & Permissions

### Permissions Setup

#### iOS (`ios/PingBee/Info.plist`)
Ensure you request microphone and audio recording permissions:
```xml
<key>NSMicrophoneUsageDescription</key>
<string>PingBee needs microphone access to record voice messages.</string>
```

#### Android (`android/app/src/main/AndroidManifest.xml`)
```xml
<uses-permission android:name="android.permission.RECORD_AUDIO" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
```

### Libraries
Depending on whether the app uses Expo or Bare React Native:
- **Expo**: `expoinstall expo-av` (Recommended)
- **Bare React Native**: `npm install react-native-audio-recorder-player`

---

## 3. HTTP API Reference

### POST `/messages/upload-audio`

Uploads the recorded audio file to the backend. The backend will automatically upload it to **Oracle Cloud Object Storage** (or fallback directory in development) and return a public HTTPS URL.

* **Headers**:
  * `Content-Type: multipart/form-data`
  * `Authorization: Bearer <JWT_ACCESS_TOKEN>`
* **Body (Multipart Form-Data)**:
  * `file`: The recorded audio file binary (supported types: `audio/aac`, `audio/mp4`, `audio/wav`, `audio/webm`, `audio/ogg`).
  * `duration_seconds`: Integer representation of the recorded duration in seconds.
* **Success Response (200 OK)**:
  ```json
  {
    "success": true,
    "status": 200,
    "message": "Audio uploaded successfully",
    "data": {
      "audio_url": "https://objectstorage.ap-hyderabad-1.oraclecloud.com/n/axdapbu0yxvy/b/pingbee-bucket/o/audio/a67cafcf-d9df-4180-9f24-58fb524be8af.wav",
      "duration_seconds": 5
    }
  }
  ```

---

## 4. WebSocket Events (Real-Time Communication)

Once the upload succeeds, transmit the message metadata over the existing WebSocket connection.

### Send Message Event (Client ──► Server)
Add `type`, `audioUrl`, and `durationSeconds` to the standard `SEND_MSG` wrapper payload:

```json
{
  "event": "SEND_MSG",
  "payload": {
    "id": "client-generated-uuid-or-timestamp",
    "chatId": 12,
    "text": "", 
    "type": "audio",
    "audioUrl": "https://objectstorage.ap-hyderabad-1.oraclecloud.com/n/axdapbu0yxvy/b/pingbee-bucket/o/audio/a67cafcf-d9df-4180-9f24-58fb524be8af.wav",
    "durationSeconds": 5,
    "replyTo": null,
    "createdAt": "2026-06-22T23:30:00Z"
  }
}
```

### Receive Message Event (Server ──► Client)
When receiving the `RECEIVE_MSG` event, check the `type` field. If it is `"audio"`, render the Voice Bubble UI using `audioUrl` and `durationSeconds`:

```json
{
  "event": "RECEIVE_MSG",
  "payload": {
    "id": "client-generated-uuid-or-timestamp",
    "chatId": "12",
    "text": "",
    "senderId": "45",
    "createdAt": "2026-06-22T17:59:38Z",
    "serverTimestamp": "2026-06-22T17:59:38Z",
    "isDeletedForEveryone": false,
    "isEdited": false,
    "replyTo": null,
    "isBot": false,
    "type": "audio",
    "audioUrl": "https://objectstorage.ap-hyderabad-1.oraclecloud.com/n/axdapbu0yxvy/b/pingbee-bucket/o/audio/a67cafcf-d9df-4180-9f24-58fb524be8af.wav",
    "durationSeconds": 5
  },
  "timestamp": "2026-06-22T17:59:38Z"
}
```

---

## 5. Fetching History & Conversation APIs

### 1. Chat History (`POST /messages`)
When downloading messages inside a chat room, the returned message items now include the audio details:
```json
{
  "success": true,
  "status": 200,
  "message": "Messages fetched successfully",
  "data": {
    "messages": [
      {
        "message_id": "uuid-12345",
        "sender_id": 45,
        "message": "",
        "created_at": "2026-06-22T17:59:38Z",
        "is_read": true,
        "is_edited": false,
        "is_deleted_for_everyone": false,
        "is_delete_for_me": false,
        "reply_to": null,
        "message_type": "audio",
        "media_url": "https://objectstorage.ap-hyderabad-1.oraclecloud.com/n/axdapbu0yxvy/b/pingbee-bucket/o/audio/a67cafcf-d9df-4180-9f24-58fb524be8af.wav",
        "duration_seconds": 5
      }
    ]
  }
}
```

### 2. Conversation List (`GET /chats`)
If the last message in a chat conversation was a voice message, `last_message_text` will automatically be formatted as:
`"last_message_text": "🎙️ Voice message"`

---

## 6. Implementation Example (Expo Audio Setup)

Here is a simplified example of how to handle recording and uploading using `expo-av`.

```javascript
import React, { useState } from 'react';
import { Button, View, Text } from 'react-native';
import { Audio } from 'expo-av';

export default function VoiceMessaging({ chatId, socket, userToken }) {
  const [recording, setRecording] = useState(null);
  const [recordingUri, setRecordingUri] = useState(null);
  const [duration, setDuration] = useState(0);

  // 1. Start Recording
  async function startRecording() {
    try {
      await Audio.requestPermissionsAsync();
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(recording);
    } catch (err) {
      console.error('Failed to start recording', err);
    }
  }

  // 2. Stop Recording
  async function stopRecording() {
    if (!recording) return;
    setRecording(undefined);
    await recording.stopAndUnloadAsync();
    
    const uri = recording.getURI(); 
    setRecordingUri(uri);

    // Get exact duration
    const status = await recording.getStatusAsync();
    const durationSec = Math.round(status.durationMillis / 1000);
    setDuration(durationSec);

    // Prompt upload
    await uploadAndSendAudio(uri, durationSec);
  }

  // 3. Upload & Send
  async function uploadAndSendAudio(uri, durationSec) {
    const formData = new FormData();
    formData.append('file', {
      uri: Platform.OS === 'ios' ? uri.replace('file://', '') : uri,
      type: 'audio/mp4', // Fits AAC/m4a encoding preset
      name: 'voice.m4a',
    });
    formData.append('duration_seconds', durationSec);

    try {
      const response = await fetch('http://YOUR_SERVER_IP:8001/messages/upload-audio', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${userToken}`,
          'Content-Type': 'multipart/form-data',
        },
        body: formData,
      });

      const result = await response.json();
      if (result.success) {
        const { audio_url, duration_seconds } = result.data;

        // Emit through WebSocket
        socket.send(JSON.stringify({
          event: "SEND_MSG",
          payload: {
            id: Date.now().toString(), // local unique ID
            chatId: chatId,
            text: "",
            type: "audio",
            audioUrl: audio_url,
            durationSeconds: duration_seconds
          }
        }));
      }
    } catch (error) {
      console.error('Audio upload failed:', error);
    }
  }

  return (
    <View style={{ padding: 20 }}>
      <Button
        title={recording ? "Stop Recording" : "Hold to Record"}
        onPressIn={startRecording}
        onPressOut={stopRecording}
      />
      {recordingUri && <Text>Recorded local path: {recordingUri}</Text>}
    </View>
  );
}
```

---

## 7. Playback Bubble UI Implementation (Example)

When presenting an audio bubble inside your message feeds:

```javascript
import React, { useState, useEffect } from 'react';
import { TouchableOpacity, Text, StyleSheet } from 'react-native';
import { Audio } from 'expo-av';
import Icon from 'react-native-vector-icons/Ionicons'; // or similar vector icon lib

export function AudioMessageBubble({ audioUrl, durationSeconds, isMe }) {
  const [sound, setSound] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);

  async function playSound() {
    if (sound) {
      await sound.playAsync();
      setIsPlaying(true);
    } else {
      const { sound: newSound } = await Audio.Sound.createAsync(
        { uri: audioUrl },
        { shouldPlay: true }
      );
      setSound(newSound);
      setIsPlaying(true);

      newSound.setOnPlaybackStatusUpdate((status) => {
        if (status.didJustFinish) {
          setIsPlaying(false);
          newSound.unloadAsync();
          setSound(null);
        }
      });
    }
  }

  async function pauseSound() {
    if (sound) {
      await sound.pauseAsync();
      setIsPlaying(false);
    }
  }

  useEffect(() => {
    return sound ? () => sound.unloadAsync() : undefined;
  }, [sound]);

  return (
    <TouchableOpacity 
      onPress={isPlaying ? pauseSound : playSound} 
      style={[styles.bubble, isMe ? styles.bubbleMe : styles.bubbleThem]}
    >
      <Icon name={isPlaying ? "pause" : "play"} size={24} color="#fff" />
      <Text style={styles.durationText}>
        {Math.floor(durationSeconds / 60)}:{(durationSeconds % 60).toString().padStart(2, '0')}
      </Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  bubble: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderRadius: 20,
    marginVertical: 4,
    maxWidth: '70%',
  },
  bubbleMe: {
    backgroundColor: '#0084ff',
    alignSelf: 'flex-end',
  },
  bubbleThem: {
    backgroundColor: '#3e3e3e',
    alignSelf: 'flex-start',
  },
  durationText: {
    color: '#fff',
    marginLeft: 8,
    fontSize: 14,
  }
});
```
