"""
Auto-generate a .env file with a secure random SECRET_KEY.
Run this once on PythonAnywhere (or any new server) to create the .env file.
Usage: python create_env.py
"""
import secrets
import os

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

def generate_secret_key():
    """Generate a 50-character Django secret key."""
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(50))

def create_env_file():
    if os.path.exists(ENV_PATH):
        overwrite = input(f'.env already exists at {ENV_PATH}. Overwrite? (y/N): ')
        if overwrite.lower() != 'y':
            print('Aborted.')
            return

    secret_key = generate_secret_key()
    
    env_content = f"""# Tweety Django Settings — AUTO-GENERATED
# Do NOT commit this file to git!

SECRET_KEY={secret_key}
DEBUG=False
"""
    
    with open(ENV_PATH, 'w') as f:
        f.write(env_content)
    
    print(f'✅ .env file created at: {ENV_PATH}')
    print(f'   SECRET_KEY: {secret_key[:10]}...')
    print(f'   DEBUG: False')
    print()
    print('⚠️  Make sure .env is in your .gitignore!')

if __name__ == '__main__':
    create_env_file()
