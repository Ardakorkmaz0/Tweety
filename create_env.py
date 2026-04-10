"""
Generates a .env file with a random SECRET_KEY for local development.
Run this once after cloning: python create_env.py
"""
import secrets
import os

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')

def generate_env():
    if os.path.exists(ENV_PATH):
        overwrite = input('.env file already exists. Overwrite? (y/N): ').strip().lower()
        if overwrite != 'y':
            print('Skipped. Existing .env file kept.')
            return

    secret_key = secrets.token_urlsafe(50)
    
    env_content = f"""# Django Settings
SECRET_KEY={secret_key}

# Environment: 'development' for local, 'production' for server
# ENVIRONMENT=development
"""
    
    with open(ENV_PATH, 'w') as f:
        f.write(env_content)
    
    print(f'✅ .env file created at {ENV_PATH}')
    print('   ENVIRONMENT defaults to development (local mode).')
    print('   Set ENVIRONMENT=production on your server.')

if __name__ == '__main__':
    generate_env()
