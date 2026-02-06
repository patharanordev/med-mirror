# MedMirror Mobile (iPad Client)

A Flutter-based native client for the MedMirror system. Designed for iPad to resolve camera access issues and provide a smoother, native experience.

## Features
-   **Native Camera**: High-performance preview without browser restrictions.
-   **Real-time Segmentation**: Sends camera frames to the backend and overlays the result.
-   **Voice Chat**: Native VAD (Voice Activity Detection) and Speech-to-Text.
-   **Configurable Host**: Easily connect to your main PC running the Docker services.

## Prerequisites
-   [Flutter SDK](https://docs.flutter.dev/get-started/install) installed.
-   **macOS is REQUIRED** to build and deploy to iPad/iPhone (due to Apple's Xcode requirement).
-   If you are on Windows, you can only build for Android or Web.
-   An iPad connected via USB (on Mac).
-   The backend services (`segmentation`, `agent`, `ollama`) running on your PC.

## Setup

1.  **Get Dependencies**:
    ```bash
    flutter pub get
    ```

2.  **iOS Permissions**:
    Ensure `ios/Runner/Info.plist` has:
    -   `NSCameraUsageDescription`
    -   `NSMicrophoneUsageDescription`
    *(These are standard in new Flutter projects, but verify if deploying).*

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
-   **Camera/Mic Denied**: Check device settings -> Privacy.
