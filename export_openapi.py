import json
import subprocess
import os
from main import app

def export_openapi():
    # Set server URL for production if needed, or leave default
    openapi_schema = app.openapi()
    
    # Save JSON
    with open("openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print("OpenAPI schema exported to openapi.json")
    
    # Generate TypeScript types using openapi-typescript
    # We use npx to ensure the tool is available without global install
    print("Generating TypeScript types...")
    try:
        # On Windows, shell=True is often needed for npx
        result = subprocess.run(
            ["npx", "openapi-typescript", "openapi.json", "-o", "schema.ts"], 
            check=True, 
            shell=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        print("TypeScript types generated in schema.ts")
    except subprocess.CalledProcessError as e:
        print(f"Error generating TypeScript types: {e.stderr}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    export_openapi()
