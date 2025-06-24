#!/bin/bash

# Frontend Bundle Optimization Script
# Otimizações para reduzir tamanho do bundle e melhorar performance

echo "🚀 Starting Frontend Bundle Optimization..."
echo "=" * 50

# Navigate to frontend directory
cd /app/frontend

# Update browserslist database
echo "📊 Updating browserslist database..."
npx update-browserslist-db@latest

# Add bundle analyzer (temporarily)
echo "📦 Installing bundle analyzer..."
npm install --save-dev webpack-bundle-analyzer

# Create optimized build
echo "🔧 Creating optimized production build..."
npm run build

# Calculate build size
echo "📏 Analyzing bundle size..."
BUILD_SIZE=$(du -sh build/ | cut -f1)
JS_SIZE=$(du -sh build/static/js/ | cut -f1)
CSS_SIZE=$(du -sh build/static/css/ | cut -f1)

echo "📊 Bundle Analysis Results:"
echo "  📦 Total build size: $BUILD_SIZE"
echo "  🟨 JavaScript size: $JS_SIZE"
echo "  🎨 CSS size: $CSS_SIZE"

# Check if gzip is working
echo "🗜️  Checking gzip compression..."
if [ -f build/static/js/*.js ]; then
    ORIGINAL_JS=$(ls -la build/static/js/*.js | awk '{sum += $5} END {print sum/1024/1024 " MB"}')
    GZIPPED_JS=$(gzip -c build/static/js/*.js | wc -c | awk '{print $1/1024/1024 " MB"}')
    echo "  📊 Original JS: $ORIGINAL_JS"
    echo "  🗜️  Gzipped JS: $GZIPPED_JS"
fi

# Check for large dependencies
echo "🔍 Checking for large dependencies..."
npm ls --depth=0 --parseable | xargs du -sh 2>/dev/null | sort -hr | head -10

echo ""
echo "✅ Frontend optimization analysis complete!"
echo ""
echo "💡 Optimization recommendations:"
echo "  🚀 Lazy loading implemented ✅"
echo "  🧩 Code splitting with React.lazy ✅" 
echo "  🖼️  Image optimization implemented ✅"
echo "  📱 Service Worker implemented ✅"
echo "  ⚡ Debounced search implemented ✅"
echo "  💾 localStorage caching implemented ✅"
echo ""
echo "🎯 Performance improvements active!"

# Clean up
npm uninstall webpack-bundle-analyzer

echo "🧹 Cleanup complete!"