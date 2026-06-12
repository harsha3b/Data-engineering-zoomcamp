# python3 
'''
This script reads key-value pairs from a .env file, 
encodes the values using base64 to .env_encoded file with the prefix SECRET_ for each key.'''


"""
Reference bash command to achieve the same result:
while IFS='='read -r key value; do
    echo "SECRET_$key=$(echo -n "$value" | base64)"
done < .env >.env_encoded

"""

'''
this python script is the equivalent of the below bash command in python,
, it reads from .env, encodes the values to base64 and writes to 
.env_encoded with the prefix SECRET_ for each key.'''

'PYSCRIPT'
import base64

# Read from .env and encode to .env_encoded
with open('.env', 'r') as f:
    with open('.env_encoded', 'w') as out:
        for line in f:
            line = line.strip()
            if line and '=' in line:
                key, value = line.split('=', 1)
                encoded = base64.b64encode(value.encode()).decode()
                out.write(f"SECRET_{key}={encoded}\n")

print("✓ .env_encoded created successfully!")