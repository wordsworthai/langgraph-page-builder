import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def check_env_vars():
    """Check if all required environment variables are set."""
    required_vars = {
        "ENVIRONMENT": os.getenv("ENVIRONMENT", "local"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY"),
        "RAPIDAPI_KEY": os.getenv("RAPIDAPI_KEY"),
        "RAPIDAPI_HOST": os.getenv("RAPIDAPI_HOST"),
        "ACCESS_KEY_ID": os.getenv("ACCESS_KEY_ID"),
        "SECRET_ACCESS_KEY": os.getenv("SECRET_ACCESS_KEY"),
    }
    # Failed to get S3 client: AWS credentials not found in environment variables
    
    optional_vars = {
        "LANGFUSE_HOST": os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        "MONGO_CONNECTION_URI": os.getenv("MONGO_CONNECTION_URI"),
        "REDIS_HOST": os.getenv("REDIS_HOST", "localhost"),
        "REDIS_PORT": os.getenv("REDIS_PORT", "6379"),
    }
    
    print("=" * 80)
    print("ENVIRONMENT VARIABLES CHECK")
    print("=" * 80)
    print("\n✅ REQUIRED VARIABLES:")
    missing = []
    for var, value in required_vars.items():
        if value:
            masked = "*" * min(len(str(value)), 20) if len(str(value)) > 0 else "NOT SET"
            print(f"  ✅ {var}: {masked}")
        else:
            print(f"  ❌ {var}: NOT SET")
            missing.append(var)
    
    print("\n📋 OPTIONAL VARIABLES:")
    for var, value in optional_vars.items():
        status = "✅" if value else "⚠️ "
        print(f"  {status} {var}: {value or 'NOT SET'}")
    
    print("\n" + "=" * 80)
    if missing:
        print(f"❌ MISSING REQUIRED VARIABLES: {', '.join(missing)}")
        print("\n📝 To fix this, create a .env file in the project root with:")
        print("   ENVIRONMENT=local")
        print("   OPENAI_API_KEY=your_openai_key")
        print("   ANTHROPIC_API_KEY=your_anthropic_key")
        print("   GEMINI_API_KEY=your_gemini_key")
        from pathlib import Path
        env_path = Path(__file__).resolve().parents[1] / ".env"
        print(f"\n💡 The .env file should be in: {env_path}")
        return False
    else:
        print("✅ All required environment variables are set!")
        return True