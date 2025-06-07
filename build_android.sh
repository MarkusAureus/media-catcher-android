#!/bin/bash

echo "=== Media Catcher Android Build Script ==="

# Check if buildozer is installed
if ! command -v buildozer &> /dev/null; then
    echo "Installing buildozer..."
    pip install --user buildozer
    pip install --user cython
fi

# Check for required files
echo "Checking required files..."
required_files=("main.py" "buildozer.spec" "media-catcher.png")

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Error: Missing $file"
        exit 1
    fi
done

# Clean previous builds
echo "Cleaning previous builds..."
buildozer android clean

# Build debug APK first
echo "Building debug APK..."
buildozer android debug

if [ $? -eq 0 ]; then
    echo "✓ Debug APK built successfully!"
    
    # Build release APK
    echo "Building release APK..."
    buildozer android release
    
    if [ $? -eq 0 ]; then
        echo "✓ Release APK built successfully!"
        echo ""
        echo "APK files are in the 'bin' directory:"
        ls -la bin/*.apk
        echo ""
        echo "To install on your device:"
        echo "  adb install bin/*.apk"
        echo ""
        echo "For F-Droid submission:"
        echo "  1. Fork https://gitlab.com/fdroid/fdroiddata"
        echo "  2. Add metadata/com.github.MarkusAureus.mediacatcher.yml"
        echo "  3. Submit merge request"
    fi
else
    echo "✗ Build failed!"
    echo "Common issues:"
    echo "  - Missing Android SDK/NDK"
    echo "  - Missing dependencies"
    echo "  - Java version conflicts"
fi
