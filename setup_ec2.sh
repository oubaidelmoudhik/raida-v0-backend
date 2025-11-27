#!/bin/bash

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and pip
sudo apt-get install -y python3 python3-pip python3-venv git

# Install system dependencies for Playwright
sudo apt-get install -y libwoff1 libopus0 libwebp6 libwebpdemux2 libenchant1c2a libgudev-1.0-0 libsecret-1-0 libhyphen0 libgdk-pixbuf2.0-0 libegl1 libnotify4 libxslt1.1 libevent-2.1-7 libgles2 libvpx7 libxcomposite1 libatk1.0-0 libatk-bridge2.0-0 libepoxy0 libgtk-3-0 libharfbuzz-icu0

# Create application directory
sudo mkdir -p /var/www/raida-backend
sudo chown -R ubuntu:ubuntu /var/www/raida-backend

# Navigate to app directory (assuming code is cloned here)
# cd /var/www/raida-backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
playwright install-deps chromium

# Create systemd service
sudo tee /etc/systemd/system/raida.service << EOF
[Unit]
Description=Gunicorn instance to serve Raida Backend
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/var/www/raida-backend
Environment="PATH=/var/www/raida-backend/venv/bin"
EnvironmentFile=/var/www/raida-backend/.env
ExecStart=/var/www/raida-backend/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 app:app

[Install]
WantedBy=multi-user.target
EOF

# Start and enable service
sudo systemctl start raida
sudo systemctl enable raida

# Setup Nginx (Optional but recommended)
sudo apt-get install -y nginx
sudo tee /etc/nginx/sites-available/raida << EOF
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/raida /etc/nginx/sites-enabled
sudo rm /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

echo "✅ Deployment setup complete!"
