# main.py
import uvicorn
import os
import argparse

# Get the directory containing your script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Define file paths relative to the script location
CERT_FILE = os.path.join(BASE_DIR, "certs/cert.pem")
KEY_FILE = os.path.join(BASE_DIR, "certs/key.pem")

def check_cert_files():
    
    if not (os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)):
        try:
            from generate_cert import generate_self_signed_cert
            generate_self_signed_cert(CERT_FILE,KEY_FILE)
            print("Generated new self-signed certificate and key.")
        except ImportError:
            raise RuntimeError(
                "Certificate files not found and couldn't generate new ones. "
                "Please run generate_cert.py first."
            )

if __name__ == "__main__":
    check_cert_files()
    
    parser = argparse.ArgumentParser(description='Run the FastAPI Password Manager server')
    parser.add_argument('--insecure', action='store_true', 
                      help='Run server in HTTP mode (insecure)')
    parser.add_argument('--port', type=int, default=8000,
                      help='Port to run the server on (default: 8000)')
    parser.add_argument('--host', type=str, default="0.0.0.0",
                      help='Host to run the server on (default: 0.0.0.0)')
    
    args = parser.parse_args()
    
    # Base configuration
    config = {
        "app": "password_manager:app",
        "host": args.host,
        "port": args.port,
        "reload": True
    }
    # Add SSL configuration if not in insecure mode
    if not args.insecure:
        print("Running in HTTPS mode...")
        check_cert_files()
        config.update({
            "ssl_keyfile": KEY_FILE,
            "ssl_certfile": CERT_FILE
        })
    else:
        print("Running in HTTP mode (insecure)...")
    
    uvicorn.run(**config)