# 1. Clean Flutter
fvm flutter clean
fvm flutter pub get

# 2. Scrub iOS build artifacts
cd ios
rm -rf Pods
rm -rf dev/Pods # if it exists
rm -rf Podfile.lock
rm -rf ~/Library/Developer/Xcode/DerivedData/*

# 3. Re-install
fvm flutter precache --ios
pod install
cd ..