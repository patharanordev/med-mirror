# MedMirror Mobile (iPad Client)

A Flutter-based native client for the MedMirror system. Designed for iPad to provide a seamless "Mirror" experience by leveraging native camera access and voice interaction.

## Features

-   **Native Camera**: High-performance preview without browser restrictions.
-   **Real-time Segmentation**: Sends camera frames to the backend and overlays the mask result.
-   **Voice Chat**: Hands-free interaction using native Voice Activity Detection (VAD) and Speech-to-Text.
-   **Configurable Host**: Easily connect to your main PC running the Docker services.

## Architecture

The application is built using the **MVVM-like** pattern (Model-View-Provider):

-   **`lib/main.dart`**: Entry point and Config/Main screen routing.
-   **`lib/providers/app_state.dart`**: Manage global state (Host IP, Config status).
-   **`lib/controllers/voice_controller.dart`**: Handles microphone permissions, VAD logic, and audio recording.
-   **`lib/services/api_service.dart`**: Handles all communication with the Backend (Segmentation, Chat, STT).
-   **`lib/widgets/`**: Reusable UI components:
    -   `CameraOverlayView`: Handle camera stream and segmentation loop.
    -   `ChatPanel`: The sidebar chat interface.

### How it Works

1.  **Camera & Segmentation**:
    -   `CameraOverlayView` captures a frame every 2 seconds (in Auto Mode).
    -   The frame is sent to `http://<HOST_IP>:8000/segment`.
    -   The backend returns a masked image (Base64) and skin percentage.
    -   The app overlays the mask on top of the camera feed.

2.  **Voice & Chat**:
    -   `VoiceController` initializes the microphone.
    -   It monitors amplitude to detect speech (VAD).
    -   When speech ends (silence > 1.5s), it stops recording and uploads the audio to `http://<HOST_IP>:8001/stt`.
    -   The returned text is sent to the Chat Agent (`/chat`).
    -   The Agent streams the response text, which is parsed and displayed in `ChatPanel`.

## Prerequisites

-   [Flutter SDK](https://docs.flutter.dev/get-started/install) (v3.0+)
-   **macOS is REQUIRED** to build and deploy to iPad/iPhone (due to Apple's Xcode requirement).
-   If you are on Windows, you can build for **Android** or run as a **Windows Desktop App** (though Camera support might vary).
-   The backend services (`segmentation`, `agent`, `ollama`) running on your PC.

## Setup

1.  **Get Dependencies**:
    ```bash
    flutter pub get
    ```

2.  **iOS Permissions**:
    Ensure `ios/Runner/Info.plist` has:
    -   `NSCameraUsageDescription`: "Needed for skin analysis"
    -   `NSMicrophoneUsageDescription`: "Needed for voice commands"

## Running

1.  **Find your PC's IP**: Run `ipconfig` (Windows) or `ifconfig` (Mac/Linux).
2.  **Start the App**:
    ```bash
    flutter run -d ipad
    ```
    *(Replace `ipad` with your device ID if needed).*

3.  **Connect**:
    -   On the launch screen, enter your PC's IP (e.g., `192.168.1.5`).
    -   Tap "CONNECT".

## Troubleshooting

-   **Connection Refused**: Ensure your PC firewall allows connections on ports `8000` (Segmentation) and `8001` (Agent).
-   **Camera/Mic Denied**: Check device Settings -> Privacy.
-   **Voice Not Detecting**: Speak louder or check if another app is using the mic.
-   **"Processing Voice..." hangs**: Check if the Agent service is reachable.

## Development

-   **Tests**: Run `flutter test` to verify logic.
-   **Linting**: Run `flutter analyze` to check for style issues.
