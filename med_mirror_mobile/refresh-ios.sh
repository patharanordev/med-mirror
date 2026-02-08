cd ios
rm -rf Pods Podfile.lock
pod install
cd ..
flutter clean
flutter pub get