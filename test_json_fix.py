#!/usr/bin/env python3
"""
Quick test of JSON validation and fixing functionality
"""
import sys
sys.path.insert(0, '/workspace')

from utils.validators import validate_and_fix_json

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
    print("Config Type Handling Test")
    print("=" * 80)
    print()
    
    test_values = [
        ("Dict object", {"admin-state": "enable"}, dict),
        ("JSON string", '{"admin-state": "enable"}', dict),
        ("Simple string", "enable", str),
        ("Boolean string", "true", bool),
        ("Integer string", "100", int),
    ]
    
    for desc, value, expected_type in test_values:
        print(f"{desc}: {value}")
        print(f"  Type: {type(value).__name__}")
        
        # Simulate what the connector does
        if isinstance(value, dict):
            result = value
            print(f"  ✅ Used directly as dict")
        elif isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith('{') or stripped.startswith('['):
                is_valid, result, error = validate_and_fix_json(stripped)
                if is_valid:
                    print(f"  ✅ Parsed as JSON: {result} (type: {type(result).__name__})")
                else:
                    print(f"  ❌ Failed to parse: {error}")
            else:
                # Simple value
                if stripped.lower() in ('true', 'false'):
                    result = stripped.lower() == 'true'
                    print(f"  ✅ Converted to boolean: {result}")
                elif stripped.isdigit():
                    result = int(stripped)
                    print(f"  ✅ Converted to integer: {result}")
                else:
                    result = stripped
                    print(f"  ✅ Using as string: {result}")
        
        print()


if __name__ == "__main__":
    try:
        success = test_json_validation()
        test_type_handling()
        
        if success:
            print("\n✅ All tests passed!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
