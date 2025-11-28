#!/usr/bin/env python3
"""
Standalone test of JSON validation and fixing functionality
(No external dependencies required)
"""
import json
import re
from typing import Optional, Tuple, Union


def validate_and_fix_json(json_str: str, auto_fix: bool = True) -> Tuple[bool, Optional[Union[dict, list]], Optional[str]]:
    """
    Validate JSON string and optionally attempt to fix common issues
    (Copied from utils/validators.py for standalone testing)
    """
    if not isinstance(json_str, str):
        return False, None, f"Expected string, got {type(json_str)}"
    
    json_str = json_str.strip()
    
    # First attempt: parse as-is
    try:
        parsed = json.loads(json_str)
        return True, parsed, None
    except json.JSONDecodeError as e:
        if not auto_fix:
            return False, None, str(e)
    
    # Attempt fixes
    fixed_json = json_str
    
    # Fix 1: Remove trailing commas before closing braces/brackets
    fixed_json = re.sub(r',(\s*[}\]])', r'\1', fixed_json)
    
    # Fix 2: Remove trailing commas at end of lines before closing braces/brackets
    lines = fixed_json.split('\n')
    fixed_lines = []
    
    for i, line in enumerate(lines):
        stripped_line = line.rstrip()
        
        # Check if line ends with comma
        if stripped_line.endswith(','):
            # Look ahead to see if next non-empty line starts with } or ]
            next_is_closing = False
            for j in range(i + 1, len(lines)):
                next_stripped = lines[j].strip()
                if next_stripped:
                    if next_stripped[0] in ('}', ']'):
                        next_is_closing = True
                    break
            
            # Remove trailing comma if next line is closing bracket
            if next_is_closing:
                stripped_line = stripped_line[:-1]
        
        fixed_lines.append(stripped_line if stripped_line != line.rstrip() else line)
    
    fixed_json = '\n'.join(fixed_lines)
    
    # Try parsing the fixed JSON
    try:
        parsed = json.loads(fixed_json)
        return True, parsed, None
    except json.JSONDecodeError as e:
        return False, None, f"Could not fix JSON: {str(e)}"


def test_json_validation():
    """Test various JSON scenarios"""
    
    test_cases = [
        # (description, json_string, should_succeed)
        ("Valid JSON object", '{"key": "value"}', True),
        ("Valid JSON with trailing comma", '{"key": "value",}', True),  # Should auto-fix
        ("Valid JSON array", '["item1", "item2"]', True),
        ("Invalid JSON - missing quote", '{"key": value}', False),
        ("Valid nested JSON", '{"outer": {"inner": "value"}}', True),
        ("Multi-line with trailing comma", '''
{
  "key1": "value1",
  "key2": "value2",
}
        '''.strip(), True),  # Should auto-fix
        ("Array with trailing comma", '["item1", "item2",]', True),  # Should auto-fix
        ("Multiple trailing commas", '{"a": 1, "b": [1, 2,], "c": 3,}', True),  # Should auto-fix
    ]
    
    print("=" * 80)
    print("JSON Validation and Auto-Fix Test")
    print("=" * 80)
    print()
    
    passed = 0
    failed = 0
    
    for i, (desc, json_str, should_succeed) in enumerate(test_cases, 1):
        print(f"Test {i}: {desc}")
        print(f"  Input: {json_str[:60]}{'...' if len(json_str) > 60 else ''}")
        
        is_valid, data, error = validate_and_fix_json(json_str, auto_fix=True)
        
        if is_valid and should_succeed:
            print(f"  ✅ PASS: Valid JSON parsed successfully")
            print(f"  Result: {data}")
            passed += 1
        elif not is_valid and not should_succeed:
            print(f"  ✅ PASS: Invalid JSON correctly rejected")
            print(f"  Error: {error}")
            passed += 1
        elif is_valid and not should_succeed:
            print(f"  ❌ FAIL: Invalid JSON was accepted")
            print(f"  Result: {data}")
            failed += 1
        else:
            print(f"  ❌ FAIL: Valid JSON was rejected")
            print(f"  Error: {error}")
            failed += 1
        
        print()
    
    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)
    
    return failed == 0


def test_type_handling():
    """Test various config value types"""
    
    print("\n" + "=" * 80)
    print("Config Type Handling Test (Simulated Connector Behavior)")
    print("=" * 80)
    print()
    
    test_values = [
        ("Dict object", {"admin-state": "enable"}),
        ("JSON string", '{"admin-state": "enable"}'),
        ("Simple string", "enable"),
        ("Boolean string true", "true"),
        ("Boolean string false", "false"),
        ("Integer string", "100"),
        ("Float string", "3.14"),
    ]
    
    for desc, value in test_values:
        print(f"{desc}:")
        print(f"  Input: {value}")
        print(f"  Type: {type(value).__name__}")
        
        # Simulate what the connector does
        if isinstance(value, dict):
            result = value
            print(f"  ✅ Used directly as dict: {result}")
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith('{') or stripped.startswith('['):
                is_valid, result, error = validate_and_fix_json(stripped)
                if is_valid:
                    print(f"  ✅ Parsed as JSON: {result} (type: {type(result).__name__})")
                else:
                    print(f"  ❌ Failed to parse: {error}")
            else:
                # Simple value - type inference
                if stripped.lower() in ('true', 'false'):
                    result = stripped.lower() == 'true'
                    print(f"  ✅ Converted to boolean: {result}")
                elif stripped.isdigit():
                    result = int(stripped)
                    print(f"  ✅ Converted to integer: {result}")
                else:
                    result = stripped
                    print(f"  ✅ Using as string: '{result}'")
        
        print()


if __name__ == "__main__":
    import sys
    
    try:
        print("Testing JSON validation and fixing functionality")
        print()
        
        success = test_json_validation()
        test_type_handling()
        
        if success:
            print("\n" + "=" * 80)
            print("✅ All JSON validation tests passed!")
            print("=" * 80)
            sys.exit(0)
        else:
            print("\n" + "=" * 80)
            print("❌ Some tests failed!")
            print("=" * 80)
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
