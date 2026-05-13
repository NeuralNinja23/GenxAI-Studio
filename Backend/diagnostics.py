import os
import ast
import traceback
import sys

def check_syntax(directory):
    errors = []
    for root, dirs, files in os.walk(directory):
        # Skip venv and caches
        if '.venv' in root or '__pycache__' in root:
            continue
            
        for file in files:
            if file.endswith('.py'):
                path = os.path.join(root, file)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        source = f.read()
                        ast.parse(source, filename=path)
                except SyntaxError as e:
                    errors.append(f"❌ SyntaxError in {path}\n   Line {e.lineno}: {e.msg}\n   {e.text.strip() if e.text else ''}")
                except Exception as e:
                    errors.append(f"❌ Error reading {path}: {e}")
    return errors

if __name__ == "__main__":
    print("🔍 Scanning GenCode Studio Backend for corruption...\n")
    
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app")
    if not os.path.exists(app_dir):
        print(f"❌ Could not find 'app' directory at {app_dir}")
        sys.exit(1)
        
    print("1️⃣ Checking Python Syntax (AST Parsing)...")
    syntax_errors = check_syntax(app_dir)
    
    if syntax_errors:
        print(f"\n⚠️ Found {len(syntax_errors)} Syntax Errors:")
        for err in syntax_errors:
            print(err)
        print("\n❌ Codebase is corrupted. Fix syntax errors before checking imports.")
        sys.exit(1)
    else:
        print("✅ No syntax errors found in any file.")
        
    print("\n2️⃣ Checking Imports (Simulating FastAPI Startup)...")
    try:
        # Add backend to path so imports work
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        
        # Try to import the main app
        import app.main
        print("✅ SUCCESS! FastAPI app loaded without any ImportErrors or broken dependencies.")
        print("\n🎉 The codebase structural integrity is solid!")
    except Exception as e:
        print("\n❌ FAILED TO LOAD APP due to broken imports/logic:")
        traceback.print_exc()
