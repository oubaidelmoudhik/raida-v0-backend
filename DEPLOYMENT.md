# AWS EC2 Deployment Guide

## Files Added/Updated

1. **requirements.txt** – Includes all dependencies (`gunicorn`, `openai`, `python-pptx`, `Jinja2`, `python-dotenv`, etc.)
2. **setup_ec2.sh** – Script to automate server setup (installs Python, Playwright, Nginx, Systemd service)
3. **pdf_generator.py** – Renamed from `main.py` for clarity
4. **app.py** – Updated to use `pdf_generator.py` and shared logic

## Deployment Steps

### 1. Launch EC2 Instance
- **OS**: Ubuntu 22.04 LTS (recommended)
- **Instance Type**: t3.small or larger (Playwright needs some RAM)
- **Security Group**: Allow inbound traffic on ports 22 (SSH), 80 (HTTP), and 443 (HTTPS)

### 2. Connect to Instance
```bash
ssh -i key.pem ubuntu@your-ec2-ip
```

### 3. Clone Repository
```bash
git clone https://github.com/oubaidelmoudhik/raida-v0-backend.git
sudo mv raida-v0-backend /var/www/raida-backend
cd /var/www/raida-backend
```

### 4. Configure Environment
Create `.env` file:
```bash
sudo nano .env
```
Add your variables:
```
OPENAI_API_KEY=your_key_here
FLASK_DEBUG=0
```

### 5. Run Setup Script
Make the script executable and run it:
```bash
chmod +x setup_ec2.sh
./setup_ec2.sh
```

This script will:
- Update system packages
- Install Python, pip, and venv
- Install Playwright dependencies and browsers
- Install Python requirements
- Set up Gunicorn as a systemd service
- Configure Nginx as a reverse proxy

### 6. Verify Deployment
- Check service status: `sudo systemctl status raida`
- Check Nginx status: `sudo systemctl status nginx`
- Visit your EC2 IP address in the browser

## Troubleshooting

- **Logs**: Check application logs with `journalctl -u raida -f`
- **Permissions**: Ensure `/var/www/raida-backend` is owned by `ubuntu:ubuntu`
- **Playwright**: If PDF generation fails, check if all system dependencies are installed (see `setup_ec2.sh`)

---

All previous Render/Railway instructions have been removed. This guide focuses on AWS EC2.
