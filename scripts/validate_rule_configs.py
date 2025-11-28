#!/usr/bin/env python3
"""
Utility script to validate and optionally fix JSON configs in audit rules
"""
import json
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import get_settings

settings = get_settings()


def validate_and_fix_rules(fix: bool = False):
    """
    Validate reference_config in all rules and optionally fix common issues
    
    Args:
        fix: If True, attempt to fix and update malformed JSON
    """
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Import here to avoid circular imports
        from models.rule import AuditRule
        from db_models import AuditRuleDB
        
        rules = session.query(AuditRuleDB).all()
        
        print(f"Checking {len(rules)} rules for JSON config issues...")
        print("=" * 80)
        
        issues_found = 0
        issues_fixed = 0
        
        for rule in rules:
            if not rule.checks:
                continue
            
            for i, check in enumerate(rule.checks):
                if not isinstance(check, dict):
                    continue
                    
                reference_config = check.get('reference_config', '')
                
                if not reference_config:
                    continue
                
                # Check if it looks like JSON
                if isinstance(reference_config, str):
                    stripped = reference_config.strip()
                    if stripped.startswith('{') or stripped.startswith('['):
                        try:
                            # Try to parse as JSON
                            json.loads(stripped)
                            # Valid JSON, no issues
                        except json.JSONDecodeError as e:
                            issues_found += 1
                            print(f"\n⚠️  Rule: {rule.name} (ID: {rule.id})")
                            print(f"   Check #{i}: {check.get('name', 'unnamed')}")
                            print(f"   Error: {e}")
                            print(f"   Config (first 200 chars): {stripped[:200]}")
                            
                            if fix:
                                # Try to fix common issues
                                fixed_config = stripped
                                
                                # Fix 1: Remove trailing commas before } or ]
                                fixed_config = fixed_config.replace(',}', '}').replace(',]', ']')
                                
                                # Fix 2: Remove trailing commas in multi-line JSON
                                lines = fixed_config.split('\n')
                                fixed_lines = []
                                for line in lines:
                                    # If line ends with comma and next non-empty line starts with } or ]
                                    if line.rstrip().endswith(','):
                                        # Check if this might be a trailing comma
                                        next_char = None
                                        for next_line in lines[lines.index(line)+1:]:
                                            next_stripped = next_line.strip()
                                            if next_stripped:
                                                next_char = next_stripped[0]
                                                break
                                        
                                        if next_char in ('}', ']'):
                                            # Remove trailing comma
                                            line = line.rstrip()[:-1]
                                    
                                    fixed_lines.append(line)
                                
                                fixed_config = '\n'.join(fixed_lines)
                                
                                try:
                                    # Validate the fix
                                    json.loads(fixed_config)
                                    
                                    # Update the check
                                    check['reference_config'] = fixed_config
                                    rule.checks[i] = check
                                    issues_fixed += 1
                                    
                                    print(f"   ✅ FIXED!")
                                    
                                except json.JSONDecodeError as e2:
                                    print(f"   ❌ Could not auto-fix: {e2}")
        
        if fix and issues_fixed > 0:
            print(f"\n{'=' * 80}")
            print(f"Committing {issues_fixed} fixes to database...")
            session.commit()
            print(f"✅ Done!")
        
        print(f"\n{'=' * 80}")
        print(f"Summary:")
        print(f"  Total rules checked: {len(rules)}")
        print(f"  Issues found: {issues_found}")
        if fix:
            print(f"  Issues fixed: {issues_fixed}")
            print(f"  Issues remaining: {issues_found - issues_fixed}")
        
        return issues_found, issues_fixed
        
    finally:
        session.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate and fix JSON configs in audit rules')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix malformed JSON configs')
    args = parser.parse_args()
    
    print("Rule Config Validator")
    print("=" * 80)
    
    if args.fix:
        print("⚠️  FIX MODE ENABLED - Will attempt to fix and update malformed configs")
        print()
    
    try:
        issues_found, issues_fixed = validate_and_fix_rules(fix=args.fix)
        
        if issues_found == 0:
            print("\n✅ No issues found!")
            sys.exit(0)
        elif args.fix and issues_fixed == issues_found:
            print("\n✅ All issues fixed!")
            sys.exit(0)
        else:
            print("\n⚠️  Some issues remain")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
