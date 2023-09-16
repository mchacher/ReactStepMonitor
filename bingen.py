import sys
import random

# Check if the correct number of command-line arguments are provided
if len(sys.argv) != 2:
    print("Usage: python write_random_bytes_to_file.py <filename>")
    sys.exit(1)

# Get the filename from the command-line argument
filename = sys.argv[1]

try:
    # Generate 196 random bytes
    random_bytes = bytes([random.randint(0, 255) for _ in range(785)])

    # Open the file in binary write mode
    with open(filename, "wb") as file:
        # Write the random bytes to the file
        file.write(random_bytes)
    print(f"Random bytes written to {filename} successfully.")
except Exception as e:
    print(f"Error writing to {filename}: {str(e)}")
