#!/bin/bash
# Bundle Analysis Script for Docker Environment
# Professional Mountain Timelapse Camera System

echo "🔍 Analyzing Skylapse Frontend Bundle..."
echo "========================================"

# Clean and build
echo "📦 Building optimized production bundle..."
npm run build > /dev/null 2>&1

if [ ! -d "dist" ]; then
    echo "❌ Build failed - dist directory not found"
    exit 1
fi

echo "✅ Build completed successfully"
echo ""

# Overall bundle size
echo "📊 Bundle Size Analysis:"
echo "------------------------"
total_size=$(du -sh dist | cut -f1)
echo "Total bundle size: $total_size"

# JavaScript chunks analysis
echo ""
echo "🔗 JavaScript Chunks:"
echo "---------------------"
find dist -name "*.js" -exec du -h {} + | sort -hr | head -10

# CSS analysis
echo ""
echo "🎨 Stylesheets:"
echo "---------------"
find dist -name "*.css" -exec du -h {} + | sort -hr

# Asset analysis
echo ""
echo "🖼️  Assets:"
echo "----------"
find dist -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.svg" -o -name "*.ico" \) -exec du -h {} + | sort -hr

# Gzipped sizes (approximate)
echo ""
echo "📦 Estimated Gzipped Sizes:"
echo "---------------------------"
find dist -name "*.js" -exec sh -c 'gzip -c "$1" | wc -c | awk "{printf \"%.1fKB %s\n\", \$1/1024, \"$1\"}"' _ {} \; | sort -nr | head -5

echo ""
echo "🎯 Bundle Optimization Summary:"
echo "-------------------------------"

# Count chunks
js_chunks=$(find dist -name "*.js" | wc -l)
css_chunks=$(find dist -name "*.css" | wc -l)

echo "JavaScript chunks: $js_chunks"
echo "CSS chunks: $css_chunks"

# Check if total gzipped size is under target
main_js=$(find dist -name "index-*.js" -exec du -k {} + | head -1 | cut -f1)
total_gzipped=$(find dist -name "*.js" -exec sh -c 'gzip -c "$1" | wc -c' _ {} \; | awk '{sum+=$1} END {printf "%.0f", sum/1024}')

echo "Main app bundle: ${main_js}KB"
echo "Total gzipped: ${total_gzipped}KB"

if [ "$total_gzipped" -lt 800 ]; then
    echo "✅ Bundle optimization SUCCESS! (${total_gzipped}KB < 800KB target)"
else
    echo "⚠️  Bundle needs optimization: ${total_gzipped}KB (target: <800KB)"
fi

echo ""
echo "📋 Docker Build Recommendations:"
echo "--------------------------------"
echo "- Use multi-stage Docker builds to exclude dev dependencies"
echo "- Enable gzip compression in nginx/reverse proxy"
echo "- Consider serving static assets from CDN"
echo "- Monitor bundle sizes in CI/CD pipeline"

echo ""
echo "🏁 Analysis complete!"
