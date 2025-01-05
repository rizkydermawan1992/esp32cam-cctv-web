from werkzeug.security import generate_password_hash, check_password_hash


pass_hash = generate_password_hash("admin123")

print(pass_hash)