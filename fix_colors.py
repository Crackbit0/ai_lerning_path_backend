#!/usr/bin/env python3
"""
Color Fix Script for AI Learning Path Generator
Automatically replaces white backgrounds and bright colors with dark glassmorphic theme
"""

import os
import shutil
from pathlib import Path

def backup_file(filepath):
    """Create a backup of the original file"""
    backup_path = f"{filepath}.backup"
    shutil.copy2(filepath, backup_path)
    print(f"✅ Backup created: {backup_path}")
    return backup_path

def fix_colors(filepath):
    """Apply color fixes to the template file"""
    print(f"\n🎨 Fixing colors in: {filepath}")
    
    # Read the file
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Track changes
    changes = 0
    
    # 1. Replace white backgrounds with glass-card
    replacements = [
        ('bg-white rounded-xl shadow-xl', 'glass-card'),
        ('bg-white rounded-lg shadow-xl', 'glass-card'),
        ('bg-white rounded-lg shadow-md', 'glass-card'),
        ('bg-white rounded-lg shadow', 'glass-card'),
        ('bg-white p-4 rounded-lg shadow', 'glass-card p-4'),
        ('bg-white p-8 rounded-xl', 'glass-card p-8'),
        ('bg-gray-100', 'glass-card'),
        ('bg-gray-50', 'glass-card'),
        ('bg-gray-200', 'glass-card'),
    ]
    
    for old, new in replacements:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            changes += count
            print(f"  ✓ Replaced '{old}' → '{new}' ({count} times)")
    
    # 2. Replace text colors
    text_replacements = [
        ('text-gray-900', 'text-white'),
        ('text-gray-800', 'text-white'),
        ('text-gray-700', 'text-secondary'),
        ('text-gray-600', 'text-secondary'),
        ('text-gray-500', 'text-muted'),
        ('text-magenta', 'text-neon-purple'),
    ]

    border_replacements = [
        ('border-gray-200', 'border-transparent'),
        ('border-gray-300', 'border-glass'),
    ]
    
    for old, new in text_replacements:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            changes += count
            print(f"  ✓ Replaced '{old}' → '{new}' ({count} times)")

    for old, new in border_replacements:
        count = content.count(old)
        if count > 0:
            content = content.replace(old, new)
            changes += count
            print(f"  ✓ Replaced '{old}' → '{new}' ({count} times)")
    
    # 3. Fix specific sections
    specific_fixes = [
        # Learning Journey title
        ('<h3 class="text-2xl font-bold text-white mb-6">Your Learning Journey</h3>',
         '<h3 class="text-2xl font-bold text-white mb-6">Your Learning <span class="text-neon-cyan">Journey</span></h3>'),
        
        # Milestones title
        ('<h3 class="text-3xl font-bold text-white mb-8 text-center">Your Learning <span class="text-neon-purple">Milestones</span></h3>',
         '<h3 class="text-3xl font-bold text-white mb-8 text-center">Your Learning <span class="text-neon-purple">Milestones</span></h3>'),
    ]
    
    for old, new in specific_fixes:
        if old in content and old != new:
            content = content.replace(old, new)
            changes += 1
            print(f"  ✓ Fixed specific section")
    
    # 4. Fix Chart.js colors (if present)
    chart_fixes = [
        # Pink to Neon Cyan
        ("'rgba(255, 99, 132, 0.5)'", "'rgba(74, 216, 255, 0.3)'"),
        ("'rgba(255, 99, 132, 1)'", "'rgba(74, 216, 255, 1)'"),
        
        # Yellow to Neon Purple
        ("'rgba(255, 206, 86, 1)'", "'rgba(179, 125, 255, 1)'"),
        ("'rgba(255, 206, 86, 0.5)'", "'rgba(179, 125, 255, 0.3)'"),
    ]
    
    for old, new in chart_fixes:
        if old in content:
            content = content.replace(old, new)
            changes += 1
            print(f"  ✓ Fixed chart color")
    
    # Write the updated content
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ Applied {changes} color fixes to {filepath}")
    return changes

def main():
    """Main function to fix colors in all template files"""
    print("🎨 AI Learning Path Generator - Color Fix Script")
    print("=" * 60)
    
    # Define files to fix
    template_dir = Path("web_app/templates")
    files_to_fix = [
        template_dir / "result.html",
        template_dir / "index.html",
        template_dir / "dashboard.html",
    ]
    
    total_changes = 0
    
    for filepath in files_to_fix:
        if filepath.exists():
            # Backup first
            backup_file(filepath)
            
            # Apply fixes
            changes = fix_colors(filepath)
            total_changes += changes
        else:
            print(f"⚠️  File not found: {filepath}")
    
    print("\n" + "=" * 60)
    print(f"🎉 Color fix complete! Total changes: {total_changes}")
    print("\n📋 Next steps:")
    print("1. Review the changes in your IDE")
    print("2. Test the application")
    print("3. If issues occur, restore from .backup files")
    print("\n💡 Tip: Clear browser cache (Ctrl+Shift+R) to see changes")

if __name__ == "__main__":
    main()
