#!/usr/bin/env python3
import os
import shutil
import sys

def copy_trades():
    src = "/home/daniel/stock-logger-v5/data/trades"
    dst = "/home/daniel/stock-data-node/data/parquet"

    print(f"🚀 Starting migration of trade data...")
    print(f"📁 Source: {src}")
    print(f"📁 Destination: {dst}")
    
    if not os.path.exists(src):
        print(f"❌ Error: Source directory '{src}' does not exist.")
        sys.exit(1)

    # Walk through the source directory
    copied_count = 0
    skipped_count = 0
    error_count = 0

    for root, dirs, files in os.walk(src):
        # Determine relative path from src
        rel_path = os.path.relpath(root, src)
        dest_dir = os.path.join(dst, rel_path)
        
        # Ensure destination subdirectory exists
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
            print(f"  [DIR] Created {dest_dir}")

        for file in files:
            src_file = os.path.join(root, file)
            dest_file = os.path.join(dest_dir, file)
            
            try:
                # Copy file if it doesn't exist or is different
                # Using copy2 to preserve metadata
                shutil.copy2(src_file, dest_file)
                copied_count += 1
                # print(f"  [FILE] Copied {file}")
            except Exception as e:
                print(f"  [ERROR] Failed to copy {file}: {e}")
                error_count += 1

    print("\n" + "="*40)
    print(f"✅ Migration Complete!")
    print(f"   Files copied: {copied_count}")
    print(f"   Errors: {error_count}")
    print("="*40)

if __name__ == "__main__":
    copy_trades()
